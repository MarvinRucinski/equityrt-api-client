class HellperWrapper:
    def get_function_params(self, function_name: str):
        for func in self.cached_add_in()['Result']["functions"]:
            if func["name"] == function_name:
                return func["params"]
        return None