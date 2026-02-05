import asyncio
from mindstack_app import create_app
from mindstack_app.modules.audio.interface import AudioInterface

app = create_app()

async def test_audio():
    with app.app_context():
        print("Testing Audio Generation...")
        try:
            result = await AudioInterface.generate_audio(
                text="Hello world, this is a test.",
                engine="edge"
            )
            print("Result:", result)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_audio())
