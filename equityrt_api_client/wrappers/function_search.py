from __future__ import annotations

from typing import Callable
from typing import Any


class FunctionSearchMixin:
	_FORMULA_ID_KEY = "id"
	_DISPLAY_KEY = "text"
	_DESCRIPTION_KEY = "description"

	def interactive_function_search(
		self,
		source_code: str,
		grid_type: str = "Search",
		initial_text: str = "",
		max_results: int = 12,
		min_query_len: int = 1,
		token: str | None = None,
	) -> dict[str, Any] | None:
		"""Interactive CLI function search with live updates.

		Controls:
		- Type text to edit query
		- Enter to search (if query changed) or select highlighted result
		- Up/Down arrows to select result
		- F2 to change SourceCode (for example: PL -> US)
		- Ctrl+S or F5 as optional search shortcuts
		- Esc or q to exit without selection
		"""
		import curses

		max_results = max(1, max_results)
		min_query_len = max(0, min_query_len)

		query = initial_text
		active_source_code = source_code
		selected_idx = 0
		displayed_items: list[dict[str, Any]] = []
		status = "Type query and press Enter to search."
		last_loaded_query: str | None = None
		last_loaded_source_code: str | None = None

		def request_with_token_refresh(
			request_fn: Callable[[str | None], Any],
			explicit_token: str | None,
		) -> Any:
			response = request_fn(explicit_token)
			status = response.get("Status") if isinstance(response, dict) else None
			if status != "TokenExpire":
				return response

			reauth = getattr(self, "reauthenticate", None)
			if not callable(reauth):
				raise RuntimeError(
					"Token expired and client cannot reauthenticate. "
					"Provide credentials and call authenticate() first."
				)

			new_token = reauth()
			return request_fn(new_token)

		def load_items() -> tuple[list[dict[str, Any]], str]:
			if len(query) < min_query_len:
				return [], f"Type at least {min_query_len} character(s)."

			try:
				response = request_with_token_refresh(
					lambda auth_token: self.function_list_search_field(
						text=query,
						source_code=active_source_code,
						token=auth_token,
					),
					token,
				)
			except Exception as exc:
				return [], f"Search failed: {exc}"

			status = response.get("Status") if isinstance(response, dict) else None
			if status and status != "Ok":
				message = response.get("Message") if isinstance(response, dict) else None
				return [], f"Search failed: status={status}, message={message}"

			extracted = self._extract_function_items(response)
			if not extracted:
				return [], "No matching functions."
			return extracted[:max_results], f"{len(extracted)} result(s)."

		def render(stdscr: Any) -> None:
			stdscr.erase()
			height, width = stdscr.getmaxyx()

			stdscr.addnstr(0, 0, "EquityRT Function Search", width - 1)
			stdscr.addnstr(1, 0, "Type query | Enter search/select | ↑/↓ move | F2 source | Esc quit", width - 1)
			stdscr.addnstr(2, 0, f"Source: {active_source_code} | GridType: {grid_type}", width - 1)
			stdscr.addnstr(3, 0, f"> {query}", width - 1)
			stdscr.addnstr(4, 0, status, width - 1)

			description_start = max(6, height - 3)
			visible_rows = max(0, description_start - 6)
			for idx, item in enumerate(displayed_items[:visible_rows]):
				display = str(item.get("_display") or item.get("text") or "")
				line = display
				attr = curses.A_REVERSE if idx == selected_idx else curses.A_NORMAL
				stdscr.addnstr(6 + idx, 0, line, width - 1, attr)

			description = ""
			if displayed_items and 0 <= selected_idx < len(displayed_items):
				description = str(displayed_items[selected_idx].get(self._DESCRIPTION_KEY) or "").strip()
			if not description:
				description = "No description available for selected function."

			stdscr.addnstr(description_start, 0, "Description:", width - 1)
			for i, desc_line in enumerate(self._wrap_text(description, width - 1, max_lines=2)):
				line_no = description_start + 1 + i
				if line_no < height:
					stdscr.addnstr(line_no, 0, desc_line, width - 1)

			stdscr.refresh()

		def event_loop(stdscr: Any) -> dict[str, Any] | None:
			nonlocal query, active_source_code, selected_idx, displayed_items, status
			nonlocal last_loaded_query, last_loaded_source_code

			def change_source_code() -> None:
				nonlocal active_source_code, status, last_loaded_source_code
				prompt = "New SourceCode (for example: PL, US, DE): "
				height, width = stdscr.getmaxyx()
				line = min(height - 1, 5)
				stdscr.move(line, 0)
				stdscr.clrtoeol()
				stdscr.addnstr(line, 0, prompt, width - 1)
				stdscr.refresh()

				# Temporarily switch to blocking input for a reliable prompt experience.
				stdscr.timeout(-1)
				curses.echo()
				try:
					raw_value = stdscr.getstr(
						line,
						min(len(prompt), max(0, width - 1)),
						16,
					)
				finally:
					curses.noecho()
					stdscr.timeout(80)

				new_value = raw_value.decode("utf-8", errors="ignore").strip().upper()
				if not new_value:
					status = "Source unchanged."
					return

				if new_value == active_source_code:
					status = f"Source already set to {active_source_code}."
					return

				active_source_code = new_value
				last_loaded_source_code = None
				status = f"Source changed to {active_source_code}. Press Enter to search."

			def run_search() -> None:
				nonlocal displayed_items, status, selected_idx, last_loaded_query, last_loaded_source_code
				if len(query) < min_query_len:
					status = f"Type at least {min_query_len} character(s)."
					return

				status = "Searching..."
				render(stdscr)
				displayed_items, status = load_items()
				selected_idx = 0 if displayed_items else 0
				last_loaded_query = query
				last_loaded_source_code = active_source_code

			try:
				curses.curs_set(1)
			except curses.error:
				pass
			stdscr.keypad(True)
			stdscr.timeout(80)

			while True:
				render(stdscr)
				try:
					key = stdscr.get_wch()
				except curses.error:
					continue

				if isinstance(key, str):
					if key == "\x1b":
						return None

					if key in ("\n", "\r"):
						if query != last_loaded_query or active_source_code != last_loaded_source_code:
							run_search()
							continue

						if not displayed_items:
							status = "No result selected. Change query and press Enter to search."
							continue

						selected_item = displayed_items[selected_idx]
						formula_object_id_raw = selected_item.get(self._FORMULA_ID_KEY)
						formula_object_id = (
							str(formula_object_id_raw)
							if formula_object_id_raw is not None and formula_object_id_raw != ""
							else None
						)
						if not formula_object_id:
							status = "Selected item has no FormulaObjectId."
							continue

						try:
							grid_result = request_with_token_refresh(
								lambda auth_token: self.populate_formula_grid(
									formula_object_id=formula_object_id,
									source_code=active_source_code,
									grid_type=grid_type,
									token=auth_token,
								),
								token,
							)
						except Exception as exc:
							status = f"Grid request failed: {exc}"
							continue
						return {
							"query": query,
							"source_code": active_source_code,
							"selected": selected_item,
							"formula_object_id": formula_object_id,
							"populate_formula_grid": grid_result,
						}

					if key in ("\x7f", "\b", "\x08"):
						if query:
							query = query[:-1]
							if query != last_loaded_query:
								status = "Query changed. Press Enter to search."
						continue

					# Ctrl+S starts explicit search.
					if key == "\x13":
						run_search()
						continue

					if key.lower() == "q" and not query:
						return None

					if key.isprintable() and key not in ("\t",):
						query += key
						if query != last_loaded_query:
							status = "Query changed. Press Enter to search."
					continue

				if key == curses.KEY_UP:
					if displayed_items:
						selected_idx = max(0, selected_idx - 1)
					continue

				if key == curses.KEY_DOWN:
					if displayed_items:
						selected_idx = min(len(displayed_items) - 1, selected_idx + 1)
					continue

				if key == curses.KEY_F5:
					run_search()
					continue

				if key == curses.KEY_F2:
					change_source_code()
					continue

				if key in (curses.KEY_BACKSPACE,):
					if query:
						query = query[:-1]
						if query != last_loaded_query:
							status = "Query changed. Press Enter to search."
					continue

		try:
			return curses.wrapper(event_loop)
		except KeyboardInterrupt:
			return None

	def _extract_function_items(self, payload: Any) -> list[dict[str, Any]]:
		if payload is None:
			return []

		tree_items = self._extract_tree_function_items(payload)
		if tree_items:
			return tree_items

		candidates: list[dict[str, Any]] = []

		def visit(node: Any) -> None:
			if isinstance(node, dict):
				node_id = node.get(self._FORMULA_ID_KEY)
				node_text = node.get(self._DISPLAY_KEY)
				node_function = str(node.get("function") or "").strip()
				if "function" in node and not node_function:
					pass
				elif node_id is not None and node_id != "" and node_text is not None and node_text != "":
					candidates.append(node)
				for value in node.values():
					visit(value)
				return

			if isinstance(node, list):
				for value in node:
					visit(value)

		visit(payload)

		# Keep stable ordering while removing duplicates.
		seen: set[tuple[str, str]] = set()
		unique: list[dict[str, Any]] = []
		for item in candidates:
			marker = (
				str(item.get(self._FORMULA_ID_KEY) or ""),
				str(item.get(self._DISPLAY_KEY) or ""),
			)
			if marker in seen:
				continue
			seen.add(marker)
			unique.append(item)
		return unique

	def _extract_tree_function_items(self, payload: Any) -> list[dict[str, Any]]:
		root = payload.get("Formulas")

		results: list[dict[str, Any]] = []

		def visit(node: Any, trail: list[str]) -> None:
			if isinstance(node, list):
				for entry in node:
					visit(entry, trail)
				return

			if not isinstance(node, dict):
				return

			node_text = str(node.get("text") or "").strip()
			next_trail = trail + ([node_text] if node_text else [])

			node_id = node.get("id")
			node_function = str(node.get("function") or "").strip()
			node_description = str(node.get("description") or "").strip()
			children = node.get("children")

			if node_id and node_function:
				path = " > ".join(next_trail)
				display = path if path else node_text

				results.append(
					{
						"id": str(node_id),
						"function": node_function,
						"text": node_text,
						"description": node_description,
						"_display": display,
						"_path": path,
					}
				)

			if children:
				visit(children, next_trail)

		visit(root, [])

		# Deduplicate while keeping server order.
		seen: set[str] = set()
		unique: list[dict[str, Any]] = []
		for item in results:
			formula_id = str(item.get("id") or "")
			if not formula_id or formula_id in seen:
				continue
			seen.add(formula_id)
			unique.append(item)

		return unique

	def _wrap_text(self, text: str, width: int, max_lines: int = 2) -> list[str]:
		if width <= 0:
			return []

		words = text.split()
		if not words:
			return [""]

		lines: list[str] = []
		current = words[0]
		for word in words[1:]:
			candidate = f"{current} {word}"
			if len(candidate) <= width:
				current = candidate
			else:
				lines.append(current)
				current = word
				if len(lines) >= max_lines:
					break

		if len(lines) < max_lines:
			lines.append(current)

		if len(lines) > max_lines:
			lines = lines[:max_lines]

		if len(lines) == max_lines and len(" ".join(words)) > sum(len(l) for l in lines):
			if len(lines[-1]) >= 3:
				lines[-1] = lines[-1][: max(0, width - 3)] + "..."
		return lines
