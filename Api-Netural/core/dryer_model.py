# 烘丝机出口水分预测模型
# 支持 LSTM / GRU / Transformer 三种架构
# 输入: N个工艺特征 → 输出: 出口含水率预测值
import torch
import torch.nn as nn
import math


class DryerModel(nn.Module):
    """
    烘丝机出口水分预测模型

    架构: FeatureWeight → Encoder(LSTM/GRU/Transformer) → MultiHeadAttention → FC
    - FeatureWeight: 可学习的特征权重 (Sigmoid 门控)
    - Encoder: 时序特征提取 (LSTM / GRU / Transformer 可选)
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
        num_heads: int = 4,
        model_type: str = "lstm"  # "lstm" | "gru" | "transformer"
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.model_type = model_type.lower()

        # ---- 可学习特征权重 (Sigmoid 门控) ----
        self.feature_weights = nn.Parameter(torch.ones(input_dim))

        # ---- 输入映射 ----
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout * 0.5)
        )

        # ---- 时序编码器 (按 model_type 选择) ----
        if self.model_type == "gru":
            self.encoder = nn.GRU(
                input_size=hidden_dim,
                hidden_size=hidden_dim,
                num_layers=num_layers,
                batch_first=True,
                dropout=dropout if num_layers > 1 else 0,
                bidirectional=False
            )
        elif self.model_type == "transformer":
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=hidden_dim,
                nhead=num_heads,
                dim_feedforward=hidden_dim * 4,
                dropout=dropout,
                batch_first=True,
                activation="gelu"
            )
            self.encoder = nn.TransformerEncoder(
                encoder_layer,
                num_layers=num_layers
            )
            self.pos_encoding = PositionalEncoding(hidden_dim, dropout)
        else:
            # 默认 LSTM
            self.encoder = nn.LSTM(
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

        # 时序编码
        if self.model_type == "transformer":
            x = self.pos_encoding(x)
            enc_out = self.encoder(x)
        else:
            enc_out, _ = self.encoder(x)

        # 多头注意力
        attn_out, attn_weights = self.attention(enc_out, enc_out, enc_out)
        attn_out = self.attn_norm(attn_out + enc_out)

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


class PositionalEncoding(nn.Module):
    """Transformer 正弦位置编码"""

    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 512):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer('pe', pe)

    def forward(self, x):
        # x: (batch, seq_len, d_model)
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


# ========== 模型推荐函数 ==========

def recommend_model(n_samples: int, n_features: int, data_variance: float = None) -> dict:
    """
    根据数据特征推荐模型类型。

    规则:
    - 数据量少 (<500) 或特征少: LSTM (更稳定，不容易过拟合)
    - 数据量中等 (500~5000): GRU (参数少，训练快)
    - 数据量大 (>5000) 且特征多: Transformer (捕捉长程依赖)
    """
    if n_samples < 500:
        model_type = "lstm"
        reason = f"数据量较少（{n_samples}行），LSTM 更稳定，不容易过拟合"
        num_layers = 1
    elif n_samples < 5000:
        model_type = "gru"
        reason = f"数据量中等（{n_samples}行），GRU 参数少、训练快，性价比最高"
        num_layers = 2
    else:
        model_type = "transformer"
        reason = f"数据量充足（{n_samples}行），Transformer 能捕捉更长程的时序依赖关系"
        num_layers = 2

    # 根据特征数调整 hidden_dim
    if n_features <= 6:
        hidden_dim = 64
    elif n_features <= 12:
        hidden_dim = 128
    else:
        hidden_dim = 256

    return {
        "model_type": model_type,
        "reason": reason,
        "recommended_config": {
            "num_layers": num_layers,
            "hidden_dim": hidden_dim,
        },
        "alternatives": [
            {"type": "lstm", "label": "LSTM", "desc": "经典时序模型，稳定性好，适合小数据"},
            {"type": "gru", "label": "GRU", "desc": "轻量级 RNN，训练快，适合中等数据"},
            {"type": "transformer", "label": "Transformer", "desc": "自注意力架构，适合大数据和长序列"},
        ]
    }
