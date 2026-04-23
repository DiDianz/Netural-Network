# 烘丝机出口水分预测模型
# LSTM + Feature Attention 架构
# 输入: 12个工艺特征 → 输出: 出口含水率预测值
import torch
import torch.nn as nn


class DryerModel(nn.Module):
    """
    烘丝机出口水分预测模型

    架构: FeatureWeight → LSTM → MultiHeadAttention → FC
    - FeatureWeight: 可学习的特征权重 (Sigmoid 门控)
    - LSTM: 时序特征提取
    - MultiHeadAttention: 多头注意力机制
    - FC: 输出层 (含不确定性估计)
    """

    def __init__(
        self,
        input_dim: int = 12,
        hidden_dim: int = 128,
        num_layers: int = 2,
        output_dim: int = 1,
        dropout: float = 0.2,
        num_heads: int = 4
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # ---- 可学习特征权重 (Sigmoid 门控) ----
        self.feature_weights = nn.Parameter(torch.ones(input_dim))

        # ---- 输入映射 ----
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout * 0.5)
        )

        # ---- LSTM 时序编码器 ----
        self.lstm = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=False
        )

        # ---- 多头注意力 ----
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True
        )
        self.attn_norm = nn.LayerNorm(hidden_dim)

        # ---- 输出头 (主预测 + 不确定性) ----
        self.output_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )

        self.uncertainty_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 4),
            nn.GELU(),
            nn.Linear(hidden_dim // 4, output_dim),
            nn.Softplus()
        )

        self._init_weights()

    def _init_weights(self):
        for name, p in self.named_parameters():
            if 'weight' in name and p.dim() >= 2:
                nn.init.xavier_uniform_(p)
            elif 'bias' in name:
                nn.init.zeros_(p)
        # feature_weights 初始化为均匀
        nn.init.ones_(self.feature_weights)

    def forward(self, x, return_attention: bool = False):
        """
        Args:
            x: (batch, seq_len, input_dim)
            return_attention: 是否返回注意力权重
        Returns:
            pred: (batch, output_dim)
            uncertainty: (batch, output_dim)
            attn_weights: (optional) attention 权重
        """
        # 特征权重门控
        weights = torch.sigmoid(self.feature_weights)
        x = x * weights.unsqueeze(0).unsqueeze(0)

        # 输入映射
        x = self.input_proj(x)

        # LSTM
        lstm_out, _ = self.lstm(x)

        # 多头注意力
        attn_out, attn_weights = self.attention(lstm_out, lstm_out, lstm_out)
        attn_out = self.attn_norm(attn_out + lstm_out)

        # 取最后时间步
        last_hidden = attn_out[:, -1, :]

        # 输出
        pred = self.output_head(last_hidden)
        uncertainty = self.uncertainty_head(last_hidden)

        if return_attention:
            return pred, uncertainty, attn_weights
        return pred, uncertainty

    def get_feature_weights(self):
        """返回当前特征权重 (归一化后)"""
        with torch.no_grad():
            weights = torch.sigmoid(self.feature_weights).cpu().numpy().tolist()
        return weights
