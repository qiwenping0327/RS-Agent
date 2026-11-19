#!/usr/bin/env python3
"""
RS-engine 所有 MCP 工具全面测试脚本
使用 GF1B 遥感数据测试各 MCP 服务器的工具
"""

import subprocess
import sys
import json
import time
import os
from pathlib import Path

TEST_DATA_DIR = Path("/root/PilotDeck/data")
TEST_OUTPUT_DIR = Path("/root/PilotDeck/data/earth_agent_output/test_all_rs_mcp")
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BAND_FILES = {
    'blue': TEST_DATA_DIR / 'test_small_blue.tif',
    'green': TEST_DATA_DIR / 'test_small_green.tif',
    'red': TEST_DATA_DIR / 'test_small_red.tif',
    'nir': TEST_DATA_DIR / 'test_small_nir.tif',
}

NDVI_OUTPUT = TEST_DATA_DIR / 'earth_agent_output' / 'test_small_ndvi.tif'

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
    timeout = 60
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

def init_and_list_tools(process):
    """初始化 MCP 服务器并获取工具列表"""
    init_response = send_mcp_request(process, 'initialize', {
        'protocolVersion': '2024-11-01',
        'capabilities': {},
        'clientInfo': {'name': 'test-client', 'version': '1.0.0'}
    })
    if 'error' in init_response:
        return None, init_response['error']
    
    tools_response = send_mcp_request(process, 'tools/list')
    if 'error' in tools_response:
        return None, tools_response['error']
    
    tools = tools_response.get('result', {}).get('tools', [])
    tool_names = [t.get('name') for t in tools]
    
    return tool_names, None

def call_tool(process, tool_name, tool_args):
    """调用工具"""
    call_response = send_mcp_request(process, 'tools/call', {
        'name': tool_name,
        'arguments': tool_args
    })
    return call_response

def test_server(server_name, test_cases):
    """测试单个 MCP 服务器"""
    print(f"\n{'='*70}")
    print(f"测试服务器: {server_name}")
    print(f"{'='*70}")
    
    process = None
    results = []
    
    try:
        process = run_mcp_server(server_name)
        time.sleep(1)
        
        tool_names, error = init_and_list_tools(process)
        if error:
            print(f"❌ 初始化失败: {error}")
            return [{'status': 'failed', 'server': server_name, 'error': f'初始化失败: {error}'}]
        
        print(f"✅ 服务器初始化成功")
        print(f"   可用工具: {tool_names}")
        
        for test_case in test_cases:
            tool_name = test_case['tool']
            description = test_case['description']
            args = test_case['args']
            
            print(f"\n--- 测试: {description} ---")
            print(f"   工具: {tool_name}")
            
            if tool_name not in tool_names:
                print(f"   ❌ 工具 {tool_name} 不在可用工具列表中")
                results.append({
                    'status': 'skipped',
                    'server': server_name,
                    'tool': tool_name,
                    'description': description,
                    'reason': '工具不在可用列表中'
                })
                continue
            
            try:
                response = call_tool(process, tool_name, args)
                
                if 'error' in response:
                    print(f"   ❌ 工具调用失败: {response['error']}")
                    results.append({
                        'status': 'failed',
                        'server': server_name,
                        'tool': tool_name,
                        'description': description,
                        'error': response['error']
                    })
                else:
                    print(f"   ✅ 工具调用成功")
                    results.append({
                        'status': 'success',
                        'server': server_name,
                        'tool': tool_name,
                        'description': description
                    })
            except Exception as e:
                print(f"   ❌ 测试异常: {e}")
                results.append({
                    'status': 'failed',
                    'server': server_name,
                    'tool': tool_name,
                    'description': description,
                    'error': str(e)
                })
        
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        results.append({'status': 'failed', 'server': server_name, 'error': f'服务器启动失败: {e}'})
    finally:
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
    
    return results

TEST_CASES = {
    'rs-index': [
        {'tool': 'calculate_batch_ndvi', 'description': 'NDVI 植被指数计算', 'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_red_paths': [str(BAND_FILES['red'])],
            'output_paths': ['test_all_rs_mcp/ndvi.tif']
        }},
        {'tool': 'calculate_batch_ndwi', 'description': 'NDWI 水体指数计算', 'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_swir_paths': [str(BAND_FILES['red'])],
            'output_paths': ['test_all_rs_mcp/ndwi.tif']
        }},
        {'tool': 'calculate_batch_evi', 'description': 'EVI 增强植被指数计算', 'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_red_paths': [str(BAND_FILES['red'])],
            'input_blue_paths': [str(BAND_FILES['blue'])],
            'output_paths': ['test_all_rs_mcp/evi.tif']
        }},
        {'tool': 'calculate_batch_fvc', 'description': 'FVC 植被覆盖度计算', 'args': {
            'input_nir_paths': [str(BAND_FILES['nir'])],
            'input_red_paths': [str(BAND_FILES['red'])],
            'output_paths': ['test_all_rs_mcp/fvc.tif']
        }}
    ],
    'rs-perception': [
        {'tool': 'threshold_segmentation', 'description': '阈值分割', 'args': {
            'input_image_path': str(BAND_FILES['nir']),
            'threshold': 1000,
            'output_path': 'test_all_rs_mcp/threshold.tif'
        }},
        {'tool': 'bbox_expansion', 'description': '边界框扩展', 'args': {
            'bboxes': [[100, 100, 200, 200]],
            'radius': 50,
            'gsd': 10
        }}
    ],
    'rs-statistics': [
        {'tool': 'coefficient_of_variation', 'description': '变异系数计算', 'args': {
            'x': [10, 12, 8, 9, 11],
            'ddof': 1
        }},
        {'tool': 'skewness', 'description': '偏度计算', 'args': {
            'x': [1, 2, 3, 4, 5],
            'bias': True
        }}
    ],
    'rs-inversion': [
        {'tool': 'band_ratio', 'description': '波段比值法计算PWV', 'args': {
            'sur_refl_b02_path': str(BAND_FILES['nir']),
            'sur_refl_b05_path': str(BAND_FILES['red']),
            'sur_refl_b17_path': str(BAND_FILES['nir']),
            'sur_refl_b18_path': str(BAND_FILES['red']),
            'sur_refl_b19_path': str(BAND_FILES['green']),
            'output_path': 'test_all_rs_mcp/pwv.tif'
        }},
        {'tool': 'ATI', 'description': '表观温度反演', 'args': {
            'input_paths': [str(BAND_FILES['nir']), str(BAND_FILES['red'])],
            'output_path': 'test_all_rs_mcp/ati.tif'
        }}
    ],
    'rs-analysis': [
        {'tool': 'compute_linear_trend', 'description': '线性趋势计算', 'args': {
            'y': [10, 20, 30, 40, 50],
            'x': [1, 2, 3, 4, 5]
        }},
        {'tool': 'autocorrelation_function', 'description': '自相关函数', 'args': {
            'x': [1, 2, 3, 4, 5, 4, 3, 2, 1],
            'max_lag': 5
        }}
    ],
    'rs-agent': [
        {'tool': 'rs_analyze', 'description': '遥感分析', 'args': {
            'input_paths': [str(BAND_FILES['nir']), str(BAND_FILES['red'])],
            'analysis_type': 'ndvi',
            'output_path': 'test_all_rs_mcp/rs_agent_ndvi.tif'
        }}
    ]
}

def main():
    """主测试函数"""
    print("\n" + "="*70)
    print("  RS-engine 所有 MCP 工具全面测试报告")
    print("  测试数据: GF1B 遥感卫星数据 (裁剪样本)")
    print("  测试日期: " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)
    
    print("\n📋 测试数据文件:")
    for band, path in BAND_FILES.items():
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"   ✅ {band}: {path} ({size_mb:.2f} MB)")
        else:
            print(f"   ❌ {band}: {path} (文件不存在)")
    
    all_results = []
    
    for server_name, test_cases in TEST_CASES.items():
        results = test_server(server_name, test_cases)
        all_results.extend(results)
    
    print("\n" + "="*70)
    print("  测试结果汇总")
    print("="*70)
    
    success_count = sum(1 for r in all_results if r['status'] == 'success')
    fail_count = sum(1 for r in all_results if r['status'] == 'failed')
    skip_count = sum(1 for r in all_results if r['status'] == 'skipped')
    
    print(f"\n📊 测试统计:")
    print(f"   总数: {len(all_results)}")
    print(f"   ✅ 成功: {success_count}")
    print(f"   ❌ 失败: {fail_count}")
    print(f"   ⏭️  跳过: {skip_count}")
    
    print("\n📝 详细结果:")
    for i, result in enumerate(all_results, 1):
        if result['status'] == 'success':
            print(f"\n   {i}. ✅ {result['server']} / {result['tool']}")
            print(f"      描述: {result['description']}")
        elif result['status'] == 'failed':
            print(f"\n   {i}. ❌ {result['server']} / {result['tool']}")
            print(f"      描述: {result.get('description', '')}")
            print(f"      错误: {result.get('error', '未知错误')}")
        elif result['status'] == 'skipped':
            print(f"\n   {i}. ⏭️  {result['server']} / {result['tool']}")
            print(f"      描述: {result['description']}")
            print(f"      原因: {result['reason']}")
    
    print("\n" + "="*70)
    
    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
