# core/model.py
import torch
import torch.nn as nn

class PredictionNet(nn.Module):
    """时序预测神经网络 — LSTM + Attention 架构"""

    # input_dim: 输入特征维度，hidden_dim: LSTM 隐藏层维度，num_layers: LSTM 层数，output_dim: 输出维度，dropout: dropout 比例
    def __init__(self, input_dim=5, hidden_dim=128, num_layers=2, output_dim=1, dropout=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # LSTM 编码器
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )

        # 多头注意力
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )

        # 输出层
        self.fc = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )

    def forward(self, x):
        # x: (batch, seq_len, input_dim)
        lstm_out, _ = self.lstm(x)                    # (batch, seq_len, hidden_dim)
        attn_out, self._attn_weights = self.attention(
            lstm_out, lstm_out, lstm_out
        )                                              # (batch, seq_len, hidden_dim)
        last_step = attn_out[:, -1, :]                # (batch, hidden_dim)
        output = self.fc(last_step)                    # (batch, output_dim)
        return output
