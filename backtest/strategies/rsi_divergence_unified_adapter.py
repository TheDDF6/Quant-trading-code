#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一RSI背离策略的回测系统适配器
"""

import sys
from pathlib import Path

# 添加统一策略模块路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from unified_strategies.rsi_divergence_unified import generate_signals