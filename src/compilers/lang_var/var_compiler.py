from lang_var.var_ast import *
from common.wasm import *
import lang_var.var_tychecker as var_tychecker
from common.compilerSupport import *


def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = var_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(x), 'i64') for x in vars]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)])


def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    if len(stmts) > 0:
        stmt = stmts.pop(0)
        match(stmt):
            case StmtExp(exp):
                return compileExp(exp) + compileStmts(stmts)
            case Assign(id, exp):
                return compileExp(exp) + [WasmInstrVarLocal('set', identToWasmId(id))] + compileStmts(stmts)
            case _:
                raise Exception("Unknown statement")
    return []


def compileExp(exp: exp) -> list[WasmInstr]:
    match exp:
        case IntConst(value):
            return [WasmInstrConst('i64', value)]
        case Name(id):
            return [WasmInstrVarLocal('get', identToWasmId(id))]
        case Call(name, args):
            compiledArgs = [instr for arg in args for instr in compileExp(arg)]
            compiledArgs.append(WasmInstrCall(identToWasmId(name)))
            return compiledArgs
        case UnOp(op, e):
            return compileExp(e) + [WasmInstrConst('i64', -1)] + [WasmInstrNumBinOp('i64', 'mul')]
            raise Exception("UnOp i dunno how")
        case BinOp(left, op, right):
            return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp('i64', compileBinOp(op))]
        case _:
            raise Exception("Unknown expression")


def identToWasmId(ident: ident) -> WasmId:
    match ident.name:
        case 'print':
            return WasmId('$print_i64')
        case 'input_int':
            return WasmId('$input_i64')
        case _:
            return WasmId('$' + ident.name)


def compileBinOp(op: binaryop) -> Literal['add', 'sub', 'mul']:
    match op:
        case Add():
            return 'add'
        case Sub():
            return 'sub'
        case Mul():
            return 'mul'
        case _:
            raise Exception("Unkonwn binary operation")


            
    
    