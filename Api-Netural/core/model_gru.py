# core/model_gru.py
import torch
import torch.nn as nn


class GRUNet(nn.Module):
    """
    GRU 预测模型
    比 LSTM 更快，参数更少，适合资源有限或需要低延迟的场景
    """

    def __init__(self, input_dim=5, hidden_dim=128, num_layers=2, output_dim=1, dropout=0.2):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers

        # GRU 编码器
        # ★ 修复：原来是 nn.Ghidden_dim 拼写错误，缺少参数
        self.gru = nn.GRU(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
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
        gru_out, _ = self.gru(x)             # (batch, seq_len, hidden_dim)
        last_step = gru_out[:, -1, :]         # (batch, hidden_dim)
        output = self.fc(last_step)           # (batch, output_dim)
        return output
