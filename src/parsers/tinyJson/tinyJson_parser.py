from parsers.common import *

type Json = str | int | dict[str, Json]

def ruleJson(toks: TokenStream) -> Json:
    return alternatives("json", toks, [ruleObject, ruleString, ruleInt])

def ruleObject(toks: TokenStream) -> dict[str, Json]:
    """Parse an object: '{' entryList '}'."""
    t = toks.lookahead()
    if t.type != 'LBRACE':
        raise ParseError(f"Expected '{{', got '{t}'")
    toks.next()  # consume '{'
    entries = ruleEntryList(toks)
    t = toks.lookahead()
    if t.type != 'RBRACE':
        raise ParseError(f"Expected '}}', got '{t}'")
    toks.next()  # consume '}'
    return entries

def ruleEntryList(toks: TokenStream) -> dict[str, Json]:
    """Parse an optional entry list."""
    t = toks.lookahead()
    if t.type != 'STRING':
        return {}
    return ruleEntryListNotEmpty(toks)

def ruleEntryListNotEmpty(toks: TokenStream) -> dict[str, Json]:
    """Parse one or more entries separated by commas."""
    k, v = ruleEntry(toks)
    result = {k: v}
    while True:
        t = toks.lookahead()
        if t.type == 'COMMA':
            toks.next()  # consume ','
            k2, v2 = ruleEntry(toks)
            result[k2] = v2
        else:
            break
    return result

def ruleEntry(toks: TokenStream) -> tuple[str, Json]:
    """Parse a single entry: string ':' value."""
    key = ruleString(toks)
    t = toks.lookahead()
    if t.type != 'COLON':
        raise ParseError(f"Expected ':', got '{t}'")
    toks.next()  # consume ':'
    val = ruleJson(toks)  # calls the already defined function
    return (key, val)

def ruleString(toks: TokenStream) -> str:
    """Parse a string token."""
    t = toks.lookahead()
    if t.type != 'STRING':
        raise ParseError(f"Expected string, got {t.type}")
    toks.next()
    return t.value.strip('"')

def ruleInt(toks: TokenStream) -> int:
    """Parse an integer token."""
    t = toks.lookahead()
    if t.type != 'INT':
        raise ParseError(f"Expected integer, got {t.type}")
    toks.next()
    return int(t.value)

def parse(code: str) -> Json:
    parser = mkLexer("./src/parsers/tinyJson/tinyJson_grammar.lark")
    tokens = list(parser.lex(code))
    log.info(f'Tokens: {tokens}')
    toks = TokenStream(tokens)
    res = ruleJson(toks)
    toks.ensureEof(code)
    return res
