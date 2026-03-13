class FunctionCall:
    def __init__(self, function, args=None):
        self.function = function
        self.args = args or {}

    def formated_args(self):
        '''
        Format the arguments for the function call.
        Returns:
        [
            {"S": "PKN:PL"},
            {"D": 2024.0},
            {"S": "CLOSE"},
            {"S": "DEFAULT"},
            {"M": ""},
            {"D": 1.0},
        ]
        '''
        formatted_args = []
        arg_values = self.args.values() if isinstance(self.args, dict) else self.args
        for value in arg_values:
            if isinstance(value, str):
                formatted_args.append({"S": str(value)})
            elif isinstance(value, (int, float)):
                formatted_args.append({"D": float(value)})
            elif not value:
                formatted_args.append({"M": str(value)})
            else:
                raise ValueError(f"Unsupported argument type: {type(value)}")

        return formatted_args
    
DEFAULT_CULTURE = {
    "DatePattern": "d.MM.yyyy",
    "DecimalSeparator": ",",
    "GroupSeparator": "_",
}

class FunctionWrapper:
    def call_functions(self, function_calls, culture_info=DEFAULT_CULTURE):
        '''
        Call a list of functions and return their results.
        input: [
            FunctionCall(function="RasDaily", args={"ticker": "PKN:PL", "date": "2024-09-30", "price_type": "CLOSE", "price_source": "DEFAULT", "additional_params": "", "version": 1}),
            FunctionCall(function="RasDaily", args={"ticker": "PKN:PL", "date": "2024-09-30", "price_type": "CLOSE", "price_source": "DEFAULT", "additional_params": "", "version": 1}),
        ]
        output: [
            123.45,
            123.45
        ]
        '''
        formated_functions = []
        for i, function_call in enumerate(function_calls):
            formated_functions.append({
                "I": i,
                "F": function_call.function,
                "A": function_call.formated_args(),
            })

        result = self.invoke(
            functions=formated_functions,
            culture_info=culture_info,
        )

        if not result.get('Status') == 'Ok':
            raise Exception(f"Function call failed with status: {result.get('Status')}, message: {result.get('Message')}")
        
        sorted_function_results = sorted(
            result.get("Results", []),
            key=lambda item: item.get("I", float("inf")),
        )

        if len(sorted_function_results) < len(function_calls):
            raise Exception("Missing results for one or more function calls")

        results = []
        for function_result in sorted_function_results:
            results.append(
                next(iter(function_result.get("V", []).values()), None),
            )

        return results