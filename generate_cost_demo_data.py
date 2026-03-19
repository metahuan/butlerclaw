#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成成本追踪器的演示数据

用法:
    python generate_cost_demo_data.py
"""

import os
import json
import random
from datetime import datetime, timedelta


def generate_demo_data():
    """生成 30 天的演示成本数据"""
    
    # 模型定价 (元/百万 tokens)
    MODEL_PRICING = {
        "gpt-4o": {"provider": "openai", "input_price": 2.5, "output_price": 10.0},
        "gpt-4o-mini": {"provider": "openai", "input_price": 0.15, "output_price": 0.6},
        "claude-3-5-sonnet": {"provider": "anthropic", "input_price": 3.0, "output_price": 15.0},
        "claude-3-haiku": {"provider": "anthropic", "input_price": 0.25, "output_price": 1.25},
        "deepseek-chat": {"provider": "deepseek", "input_price": 1.0, "output_price": 2.0},
        "deepseek-reasoner": {"provider": "deepseek", "input_price": 4.0, "output_price": 16.0},
        "moonshot/kimi": {"provider": "moonshot", "input_price": 12.0, "output_price": 12.0},
    }
    
    models = list(MODEL_PRICING.keys())
    records = []
    
    # 生成 30 天的数据
    for i in range(30):
        day = datetime.now() - timedelta(days=29-i)
        
        # 每天生成 5-20 条记录
        for _ in range(random.randint(5, 20)):
            model = random.choice(models)
            pricing = MODEL_PRICING[model]
            
            # 随机生成 token 数量
            input_tokens = random.randint(1000, 100000)
            output_tokens = random.randint(500, 50000)
            
            # 计算成本
            input_cost = input_tokens / 1000000 * pricing["input_price"]
            output_cost = output_tokens / 1000000 * pricing["output_price"]
            total_cost = input_cost + output_cost
            
            record = {
                "timestamp": day.isoformat(),
                "model": model,
                "provider": pricing["provider"],
                "api_calls": 1,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_cny": round(total_cost, 4)
            }
            records.append(record)
    
    # 构建数据文件
    data = {
        "budget": {
            "monthly_budget": 1000.0,
            "daily_limit": 100.0,
            "alert_threshold": 80.0,
            "enable_email_alert": True,
            "enable_push_alert": True,
            "alert_email": ""
        },
        "records": records
    }
    
    # 保存到文件
    config_dir = os.path.expanduser("~/.openclaw")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "cost_data.json")
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 计算统计信息
    total_cost = sum(r["cost_cny"] for r in records)
    total_calls = len(records)
    total_input = sum(r["input_tokens"] for r in records)
    total_output = sum(r["output_tokens"] for r in records)
    
    print(f"[OK] Demo data saved to: {config_path}")
    print(f"\n[Stats] Data statistics:")
    print(f"   - Total records: {total_calls}")
    print(f"   - Total cost: {total_cost:.2f} CNY")
    print(f"   - Total input tokens: {total_input:,}")
    print(f"   - Total output tokens: {total_output:,}")
    print(f"   - Avg daily cost: {total_cost/30:.2f} CNY")
    
    return config_path


if __name__ == "__main__":
    generate_demo_data()
    print("\n[Hint] Restart ButlerClaw cost panel to view data")
