import asyncio

class DummyAgent:
    def stream(self, input_data):
        yield {"structured_response": MockResponse("Hello from dummy agent!")}

    async def astream(self, input_data):
        yield {"structured_response": MockResponse("Hello from dummy async agent!")}
        await asyncio.sleep(0.1)

class MockResponse:
    def __init__(self, answer):
        self.answer = answer

agent = DummyAgent()
