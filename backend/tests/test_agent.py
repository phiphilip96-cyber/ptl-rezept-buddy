"""Agent-Schleife mit gemocktem Anthropic-Client: eine Tool-Runde, dann Text."""
from types import SimpleNamespace
from ki.agent import buddy_antworten, _tool_text


class _Stream:
    def __init__(self, ereignisse, final):
        self._e, self._f = ereignisse, final

    async def __aenter__(self): return self
    async def __aexit__(self, *a): return False

    def __aiter__(self):
        self._it = iter(self._e); return self

    async def __anext__(self):
        try: return next(self._it)
        except StopIteration: raise StopAsyncIteration

    async def get_final_message(self): return self._f


def _delta(t):
    return SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(type="text_delta", text=t))


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)
    def model_dump(self):
        return dict(self.__dict__)


class _Client:
    def __init__(self):
        self.aufrufe = 0
        self.messages = self

    def stream(self, **kw):
        self.aufrufe += 1
        if self.aufrufe == 1:
            assert kw["tools"], "Tool muss in Runde 1 angeboten werden"
            final = SimpleNamespace(stop_reason="tool_use", usage=SimpleNamespace(input_tokens=10, output_tokens=5),
                                    content=[_Block(type="tool_use", id="t1", name="naehrwerte_suchen", input={"begriff": "Haferflocken"})])
            return _Stream([], final)
        assert kw["messages"][-1]["content"][0]["type"] == "tool_result"
        final = SimpleNamespace(stop_reason="end_turn", usage=SimpleNamespace(input_tokens=20, output_tokens=8),
                                content=[_Block(type="text", text="Porridge mit 370 kcal")])
        return _Stream([_delta("Porridge "), _delta("mit 370 kcal")], final)


async def _suche(begriff):
    return [{"name_de": "Haferflocken", "kcal_100g": 370, "protein_g": 13.5, "fett_g": 7, "kh_g": 59}]


async def test_tool_runde_und_streaming():
    chunks, ergebnis = [], None
    async for art, d in buddy_antworten("SYS", [{"role": "user", "content": "Frühstück?"}], client=_Client(), such_fn=_suche):
        (chunks.append(d) if art == "text" else (ergebnis := d))
    assert "".join(chunks) == "Porridge mit 370 kcal"
    assert ergebnis.tokens_in == 30 and ergebnis.tokens_out == 13
    assert ergebnis.tool_aufrufe[0]["begriff"] == "Haferflocken"


def test_tool_text_format():
    assert "370 kcal" in _tool_text([{"name_de": "Haferflocken", "kcal_100g": 370, "protein_g": 13.5}])
    assert "Kein Treffer" in _tool_text([])
