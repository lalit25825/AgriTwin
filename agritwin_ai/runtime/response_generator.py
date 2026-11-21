from agritwin_ai.runtime.llm import ask_llm


class ResponseGenerator:

    def generate(
        self,
        agent_name,
        intent,
        decision,
        observations
    ):

        if decision is None:

            system_prompt = f"""
You are AgriTwin's {agent_name} Agent.

Your job is to explain observations produced by deterministic
tools for the user's request.

The observations are authoritative.

Never invent data that was not provided.

Never claim that data exists when the observations contain
an error or indicate that data is unavailable.

The response style must match the agent.

For Logistics requests:
- Clearly summarize the shipment.
- Explain origin and destination.
- Explain the best available route, distance and travel time.
- Mention alternative routes when available.
- Explain vehicle type, capacity and number of loads.
- Explain estimated transport cost and its components.
- Explain weather at origin and destination when available.
- Explain logistics risk and its factors.
- Clearly distinguish live data from estimates.
- Clearly state when live traffic data is unavailable.
- Clearly state when transport cost is an estimate rather than
  a transporter quotation.
- Do not confuse road-network ETA with live traffic ETA.

For Market requests:
- Explain prices, forecasts, market conditions and economics
  using only supplied observations.

For Harvest or Climate requests:
- Explain weather, crop and decision-related observations
  using only supplied observations.

Do not repeat every internal field mechanically.
Turn the supplied data into a useful, readable answer.

Never invent missing information.

Use only ASCII characters.

Return plain text only.
"""

            user_prompt = f"""
Intent:

{intent}

Observations:

{observations}

Explain the result using ONLY the supplied observations.

If the observations contain an error, clearly explain that
the requested information could not be obtained and state
the supplied reason.

If data is marked unavailable, do not guess it.

For Logistics, prioritize:
1. shipment summary
2. route and ETA
3. vehicle/load information
4. transport cost
5. weather
6. risk
7. important data-quality limitations

Keep numerical values exactly consistent with the observations.

Return only the final answer.
"""

        else:

            system_prompt = f"""
You are AgriTwin's {agent_name} Agent.

The deterministic decision has ALREADY been made by Python.

The Python Decision Engine is authoritative.

You are NOT allowed to change, override, reinterpret,
or replace the decision.

Your ONLY job is to explain the supplied decision naturally.

Never invent data.

Never invent weather.

Never invent crop information.

Never invent market information.

Never invent logistics information.

If this is a Logistics decision, explain the decision using
the supplied route, cost, vehicle, weather, risk and
data-quality observations.

Clearly distinguish estimates from live data.

Use only ASCII characters.

Return plain text only.
"""

            user_prompt = f"""
Intent:

{intent}

Deterministic Decision:

{decision}

Observations:

{observations}

Explain the deterministic decision using ONLY the supplied
observations and decision.

Do not create a different recommendation.

Return only the final answer.
"""

        response = ask_llm(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        text = response.choices[0].message.content

        text = ''.join(
            c if ord(c) < 128 else ' '
            for c in text
        )

        if decision is None:
            return text

        if (
            isinstance(decision, dict)
            and "decision" in decision
        ):
            decision_value = decision["decision"]
        else:
            decision_value = str(decision)

        return (
            f"Deterministic {agent_name} decision: "
            f"{decision_value}\n\n{text}"
        )