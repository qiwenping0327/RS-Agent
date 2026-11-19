#!/usr/bin/env python3
"""
测试遥感图像制图 skill 是否正确集成
"""

import json
import os
from pathlib import Path

def test_skill_integration():
    """测试 skill 集成"""
    print("=== 遥感图像制图 Skill 集成测试 ===")
    
    # 1. 检查 SKILL.md 文件
    skill_path = Path("/root/PilotDeck/.pilotdeck/plugins/rs-agent/skills/rs-cartography/SKILL.md")
    if skill_path.exists():
        print(f"\n✅ SKILL.md 文件存在: {skill_path}")
        with open(skill_path, 'r') as f:
            content = f.read()
            print(f"   文件大小: {len(content)} 字节")
            
            # 检查关键内容
            check_items = [
                ('遥感图像制图', '技能名称'),
                ('波段组合', '波段组合内容'),
                ('色彩调整', '色彩调整内容'),
                ('文字标注', '文字标注内容'),
                ('打印参数', '打印参数内容'),
                ('相纸', '相纸打印设置'),
                ('绢丝布', '绢丝布打印设置'),
                ('比例尺', '比例尺计算'),
            ]
            
            for item, desc in check_items:
                if item in content:
                    print(f"   ✅ 包含 {desc}")
                else:
                    print(f"   ❌ 缺少 {desc}")
    else:
        print(f"\n❌ SKILL.md 文件不存在: {skill_path}")
        return False
    
    # 2. 检查 plugin.json 配置
    plugin_json_paths = [
        "/root/PilotDeck/.pilotdeck/plugins/rs-agent/plugin.json",
        "/root/PilotDeck/products/rs-agent/plugins/rs-agent/plugin.json",
    ]
    
    print("\n=== plugin.json 配置检查 ===")
    for json_path in plugin_json_paths:
        if Path(json_path).exists():
            with open(json_path, 'r') as f:
                config = json.load(f)
            
            skills = config.get('skills', [])
            if 'skills/rs-cartography' in skills:
                print(f"✅ {json_path} 已配置 rs-cartography")
            else:
                print(f"❌ {json_path} 未配置 rs-cartography")
        else:
            print(f"⚠️ {json_path} 不存在")
    
    # 3. 检查所有位置的 skill 文件
    print("\n=== skill 文件位置检查 ===")
    skill_locations = [
        "/root/PilotDeck/.pilotdeck/plugins/rs-agent/skills/rs-cartography/SKILL.md",
        "/root/PilotDeck/products/rs-agent/plugins/rs-agent/skills/rs-cartography/SKILL.md",
    ]
    
    for loc in skill_locations:
        if Path(loc).exists():
            print(f"✅ {loc}")
        else:
            print(f"❌ {loc}")
    
    print("\n=== Skill 内容摘要 ===")
    with open(skill_path, 'r') as f:
        lines = f.readlines()
    
    print("\n工作流程阶段:")
    stage_count = 0
    for line in lines:
        if line.startswith("### 阶段"):
            stage_count += 1
            print(f"   {line.strip()}")
    
    print(f"\n共 {stage_count} 个阶段")
    
    return True

if __name__ == "__main__":
    success = test_skill_integration()
    print("\n" + "="*50)
    if success:
        print("✅ 遥感图像制图 Skill 集成测试通过")
    else:
        print("❌ 遥感图像制图 Skill 集成测试失败")
    print("="*50)
