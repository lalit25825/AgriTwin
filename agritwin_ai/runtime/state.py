import time


class AgentState:

    def __init__(self):

        self.step = 1

        self.retry_count = 0

        self.tool_calls = 0

        self.start_time = time.time()

        self.current_tool = None