class ResponseMerger:

    def merge(self, responses):

        final = []

        for response in responses:

            if response:

                final.append(response)

        return "\n\n".join(final)