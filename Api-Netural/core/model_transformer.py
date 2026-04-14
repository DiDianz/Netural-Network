# core/model_transformer.py
import torch
import torch.nn as nn
import math


class PositionalEncoding(nn.Module):
    """位置编码 — 告诉模型数据的时间顺序"""

    def __init__(self, d_model, max_len=500, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)

        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)


class TransformerNet(nn.Module):
    """
    Transformer 预测模型
    并行计算快，擅长捕捉长距离依赖
    适合数据量大、序列长的场景
    """

    def __init__(self, input_dim=5, d_model=128, nhead=4, num_layers=3,
                 dim_feedforward=256, output_dim=1, dropout=0.1):
        super().__init__()

        # 输入投影: 5维 → 128维
        self.input_proj = nn.Linear(input_dim, d_model)

        # 位置编码
        self.pos_encoder = PositionalEncoding(d_model, dropout=dropout)

        # Transformer 编码器
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            activation='gelu'
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # 输出层
        self.fc = nn.Sequential(  # type: ignore
            nn.LayerNorm(d_model),
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model // 2, output_dim)
        )

    def forward(self, x):
        # x: (batch, seq_len, input_dim)
        x = self.input_proj(x)                        # (batch, seq_len, d_model)
        x = self.pos_encoder(x)                        # 加位置编码
        x = self.transformer(x)                        # (batch, seq_len, d_model)
        x = x[:, -1, :]                                # 取最后一个时刻
        return self.fc(x)                               # type: ignore # (batch, output_dim)
