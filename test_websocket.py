"""Quick WebSocket test to verify frame streaming"""
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws"
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket conectado")
            
            # Receber 3 frames para testar
            for i in range(3):
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                if data.get("type") == "multi_frame":
                    cameras = data.get("cameras", [])
                    print(f"\n[Frame {i+1}]")
                    print(f"  Tipo: {data['type']}")
                    print(f"  Câmeras: {len(cameras)}")
                    for cam in cameras:
                        print(f"    - ID: {cam['camera_id']}")
                        print(f"      Nome: {cam['name']}")
                        print(f"      Dados: {len(cam['data'])} bytes (base64)")
                    
                    if cameras:
                        print("\n✅ WebSocket transmitindo frames corretamente!")
                        return True
            
            print("\n❌ Sem dados de câmeras nos frames")
            return False
                    
    except asyncio.TimeoutError:
        print("❌ Timeout - WebSocket não enviou frames")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    exit(0 if result else 1)
