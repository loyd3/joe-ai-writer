"""
测试 DeepSeek API 连接
直接测试 API Key 是否有效
"""
import asyncio
import httpx
import ssl

async def test_deepseek_api():
    api_key = "sk-30040f2756c64c50922fe0313fbacb38"  # 替换为你的 API Key
    base_url = "https://api.deepseek.com/v1"
    
    print("=" * 50)
    print("DeepSeek API 连接测试")
    print("=" * 50)
    
    # 1. 测试 DNS 解析
    import socket
    try:
        ip = socket.gethostbyname("api.deepseek.com")
        print(f"✓ DNS 解析成功: api.deepseek.com -> {ip}")
    except Exception as e:
        print(f"✗ DNS 解析失败: {e}")
        return
    
    # 2. 测试 HTTP 连接 (禁用 SSL)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with httpx.AsyncClient(verify=ssl_context, timeout=10.0) as client:
            response = await client.get(f"{base_url}/models", headers={"Authorization": f"Bearer {api_key}"})
            print(f"✓ HTTP 连接成功 (SSL禁用): {response.status_code}")
    except Exception as e:
        print(f"✗ HTTP 连接失败 (SSL禁用): {e}")
    
    # 3. 测试 HTTP 连接 (启用 SSL)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/models", headers={"Authorization": f"Bearer {api_key}"})
            print(f"✓ HTTP 连接成功 (SSL启用): {response.status_code}")
    except Exception as e:
        print(f"✗ HTTP 连接失败 (SSL启用): {e}")
    
    # 4. 测试 OpenAI SDK
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print(f"✓ OpenAI SDK 测试成功: {response.choices[0].message.content}")
    except Exception as e:
        print(f"✗ OpenAI SDK 测试失败: {type(e).__name__}: {e}")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_deepseek_api())
