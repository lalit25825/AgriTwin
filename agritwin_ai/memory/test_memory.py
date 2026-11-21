from agritwin_ai.memory.manager import MemoryManager


memory = MemoryManager()

# Working Memory
memory.update_working({
    "crop": "onion",
    "city": "Nashik"
})

# Semantic Memory
memory.remember_fact(
    "preferred_language",
    "Marathi"
)

# Episodic Memory
memory.remember_event(
    "Harvest Decision",
    {
        "crop": "onion",
        "decision": "Delay"
    }
)

print("========== WORKING ==========")
print(memory.get_working())

print("\n========== SEMANTIC ==========")
print(memory.recall_fact("preferred_language"))

print("\n========== LAST EVENT ==========")
print(memory.get_last_event())