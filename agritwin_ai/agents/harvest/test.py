from agritwin_ai.agents.harvest.workflow import HarvestWorkflow

workflow = HarvestWorkflow()

workflow.state.crop = "onion"
workflow.state.city = "Nashik"

print(workflow.reflect())

workflow.set_weather({

    "temperature": 23,

    "humidity": 92,

    "wind_speed": 15,

    "rain_probability": 100

})

workflow.set_crop_info({

    "ideal_temperature": {

        "min": 18,

        "max": 25

    },

    "max_humidity": 70,

    "rain_sensitive": True,

    "ideal_wind_speed": 20

})

print(workflow.ready_for_evaluation())