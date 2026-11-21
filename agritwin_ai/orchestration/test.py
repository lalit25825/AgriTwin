from agritwin_ai.orchestration.response_merger import ResponseMerger


merger = ResponseMerger()

responses = [

    "Harvest tomorrow.",

    "Sell in Lasalgaon.",

    "Store below 24°C."

]

print(

    merger.merge(

        responses

    )

)