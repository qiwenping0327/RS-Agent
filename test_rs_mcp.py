#!/usr/bin/env python3
"""
RS-engine MCP 工具测试脚本
使用 GF1B 遥感数据测试各光谱指数计算工具
"""

import subprocess
import sys
import json
import time
import os
from pathlib import Path

TEST_DATA_DIR = Path("/home/gfib_data")
TEST_OUTPUT_DIR = Path("/root/PilotDeck/data/earth_agent_output/test_rs_mcp")
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BAND_FILES = {
    'blue': Path("/root/PilotDeck/data/test_small_blue.tif"),
    'green': Path("/root/PilotDeck/data/test_small_green.tif"),
    'red': Path("/root/PilotDeck/data/test_small_red.tif"),
    'nir': Path("/root/PilotDeck/data/test_small_nir.tif"),
}

TEST_CASES = [
    {
        'server': 'rs-index',
        'tool': 'calculate_batch_ndvi',
        'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_red_paths': [str(BAND_FILES['red'])],
            'output_paths': ['test_rs_mcp/ndvi_gf1b.tif']
        },
        'description': 'NDVI 植被指数计算'
    },
    {
        'server': 'rs-index',
        'tool': 'calculate_batch_ndwi',
        'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_swir_paths': [str(BAND_FILES['red'])],
            'output_paths': ['test_rs_mcp/ndwi_gf1b.tif']
        },
        'description': 'NDWI 水体指数计算'
    },
    {
        'server': 'rs-index',
        'tool': 'calculate_batch_evi',
        'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_red_paths': [str(BAND_FILES['red'])],
            'input_blue_paths': [str(BAND_FILES['blue'])],
            'output_paths': ['test_rs_mcp/evi_gf1b.tif']
        },
        'description': 'EVI 增强植被指数计算'
    },
    {
        'server': 'rs-index',
        'tool': 'calculate_batch_fvc',
        'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_red_paths': [str(BAND_FILES['red'])],
            'output_paths': ['test_rs_mcp/fvc_gf1b.tif']
        },
        'description': 'FVC 植被覆盖度计算'
    },
]

def run_mcp_server(server_name):
    """启动 MCP 服务器进程"""
    config = {
        'rs-index': {
            'command': 'python3',
            'args': ['-m', 'rs_engine.earth_agent_tools.index'],
            'cwd': '/root/PilotDeck/rs-engine',
            'env': {
                'RS_WORKSPACE': '/root/PilotDeck/data',
                'RS_ENGINE_HOME': '/root/PilotDeck/rs-engine'
            }
        },
        'rs-perception': {
            'command': 'python3',
            'args': ['-m', 'rs_engine.earth_agent_tools.perception'],
            'cwd': '/root/PilotDeck/rs-engine',
            'env': {
                'RS_WORKSPACE': '/root/PilotDeck/data',
                'RS_ENGINE_HOME': '/root/PilotDeck/rs-engine'
            }
        },
        'rs-statistics': {
            'command': 'python3',
            'args': ['-m', 'rs_engine.earth_agent_tools.statistics'],
            'cwd': '/root/PilotDeck/rs-engine',
            'env': {
                'RS_WORKSPACE': '/root/PilotDeck/data',
                'RS_ENGINE_HOME': '/root/PilotDeck/rs-engine'
            }
        },
        'rs-inversion': {
            'command': 'python3',
            'args': ['-m', 'rs_engine.earth_agent_tools.inversion'],
            'cwd': '/root/PilotDeck/rs-engine',
            'env': {
                'RS_WORKSPACE': '/root/PilotDeck/data',
                'RS_ENGINE_HOME': '/root/PilotDeck/rs-engine'
            }
        },
        'rs-analysis': {
            'command': 'python3',
            'args': ['-m', 'rs_engine.earth_agent_tools.analysis'],
            'cwd': '/root/PilotDeck/rs-engine',
            'env': {
                'RS_WORKSPACE': '/root/PilotDeck/data',
                'RS_ENGINE_HOME': '/root/PilotDeck/rs-engine'
            }
        },
        'rs-agent': {
            'command': 'python3',
            'args': ['-m', 'rs_engine.mcp_server'],
            'cwd': '/root/PilotDeck/rs-engine',
            'env': {
                'RS_WORKSPACE': '/root/PilotDeck/data',
                'RS_ENGINE_HOME': '/root/PilotDeck/rs-engine'
            }
        }
    }
    
    cfg = config.get(server_name)
    if not cfg:
        raise ValueError(f"Unknown server: {server_name}")
    
    env = os.environ.copy()
    env.update(cfg['env'])
    
    process = subprocess.Popen(
        [cfg['command']] + cfg['args'],
        cwd=cfg['cwd'],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return process

def send_mcp_request(process, method, params=None):
    """发送 MCP 请求"""
    request = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': method,
        'params': params or {}
    }
    
    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()
    
    response_lines = []
    timeout = 30
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        line = process.stdout.readline()
        if line:
            response_lines.append(line.strip())
            if line.strip():
                try:
                    response = json.loads(line)
                    return response
                except json.JSONDecodeError:
                    continue
        time.sleep(0.1)
    
    raise TimeoutError(f"MCP request timeout after {timeout}s")

def test_mcp_server(server_name, tool_name, tool_args, description):
    """测试单个 MCP 工具"""
    print(f"\n{'='*60}")
    print(f"测试: {description}")
    print(f"服务器: {server_name}")
    print(f"工具: {tool_name}")
    print(f"参数: {json.dumps(tool_args, indent=2, default=str)}")
    print(f"{'='*60}")
    
    process = None
    try:
        process = run_mcp_server(server_name)
        time.sleep(1)
        
        print("\n1. 初始化 MCP 服务器...")
        init_response = send_mcp_request(process, 'initialize', {
            'protocolVersion': '2024-11-01',
            'capabilities': {},
            'clientInfo': {'name': 'test-client', 'version': '1.0.0'}
        })
        if 'error' in init_response:
            print(f"❌ 初始化失败: {init_response['error']}")
            return {'status': 'failed', 'description': description, 'server': server_name, 'tool': tool_name, 'error': init_response['error']}
        
        print("✅ 初始化成功")
        print(f"   Server Info: {json.dumps(init_response.get('result', {}), indent=2)}")
        
        print("\n2. 获取工具列表...")
        tools_response = send_mcp_request(process, 'tools/list')
        if 'error' in tools_response:
            print(f"❌ 获取工具列表失败: {tools_response['error']}")
            return {'status': 'failed', 'description': description, 'server': server_name, 'tool': tool_name, 'error': tools_response['error']}
        
        tools = tools_response.get('result', {}).get('tools', [])
        tool_names = [t.get('name') for t in tools]
        print(f"✅ 工具列表获取成功")
        print(f"   可用工具: {tool_names}")
        
        if tool_name not in tool_names:
            print(f"❌ 工具 {tool_name} 不在可用工具列表中")
            return {'status': 'failed', 'description': description, 'server': server_name, 'tool': tool_name, 'error': f'Tool {tool_name} not found'}
        
        print(f"\n3. 调用工具 {tool_name}...")
        call_response = send_mcp_request(process, 'tools/call', {
            'name': tool_name,
            'arguments': tool_args
        })
        
        if 'error' in call_response:
            print(f"❌ 工具调用失败: {call_response['error']}")
            return {'status': 'failed', 'description': description, 'server': server_name, 'tool': tool_name, 'error': call_response['error']}
        
        result = call_response.get('result', {})
        print(f"✅ 工具调用成功!")
        print(f"   结果: {json.dumps(result, indent=2, default=str)}")
        
        return {
            'status': 'success',
            'description': description,
            'server': server_name,
            'tool': tool_name,
            'result': result
        }
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return {'status': 'failed', 'description': description, 'server': server_name, 'tool': tool_name, 'error': str(e)}
    finally:
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()

def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("  RS-engine MCP 工具测试报告")
    print("  测试数据: GF1B 遥感卫星数据")
    print("  测试日期: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)
    
    print("\n📋 测试数据文件:")
    for band, path in BAND_FILES.items():
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"   ✅ {band}: {path} ({size_mb:.2f} MB)")
        else:
            print(f"   ❌ {band}: {path} (文件不存在)")
    
    results = []
    
    for test_case in TEST_CASES:
        result = test_mcp_server(
            test_case['server'],
            test_case['tool'],
            test_case['args'],
            test_case['description']
        )
        results.append(result)
    
    print("\n" + "="*70)
    print("  测试结果汇总")
    print("="*70)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    fail_count = len(results) - success_count
    
    print(f"\n📊 测试统计:")
    print(f"   总数: {len(results)}")
    print(f"   ✅ 成功: {success_count}")
    print(f"   ❌ 失败: {fail_count}")
    
    print("\n📝 详细结果:")
    for i, result in enumerate(results, 1):
        status_icon = "✅" if result['status'] == 'success' else "❌"
        print(f"\n   {i}. {status_icon} {result['description']}")
        print(f"      服务器: {result['server']}")
        print(f"      工具: {result['tool']}")
        if result['status'] == 'success':
            result_text = result.get('result', {}).get('text', '')
            if result_text:
                print(f"      结果: {result_text}")
        else:
            print(f"      错误: {result.get('error', '未知错误')}")
    
    print("\n📁 输出文件位置:")
    output_files = list(TEST_OUTPUT_DIR.glob('*.tif'))
    if output_files:
        for f in output_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   ✅ {f.name} ({size_mb:.2f} MB)")
    else:
        print("   ❌ 无输出文件")
    
    print("\n" + "="*70)
    
    return 0 if success_count == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())