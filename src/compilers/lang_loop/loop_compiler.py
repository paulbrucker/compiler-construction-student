from lang_loop.loop_ast import *
from common.wasm import *
import lang_loop.loop_tychecker as loop_tychecker
from common.compilerSupport import *


def compileModule(m: mod, cfg: CompilerConfig) -> WasmModule:
    """
    Compiles the given module.
    """
    vars = loop_tychecker.tycheckModule(m)
    instrs = compileStmts(m.stmts)
    idMain = WasmId('$main')
    locals: list[tuple[WasmId, WasmValtype]] = [(identToWasmId(ident), tyToWasmValtype(valtype.ty)) for ident, valtype in vars.items()]
    return WasmModule(imports=wasmImports(cfg.maxMemSize),
        exports=[WasmExport("main", WasmExportFunc(idMain))],
        globals=[],
        data=[],
        funcTable=WasmFuncTable([]),
        funcs=[WasmFunc(idMain, [], None, locals, instrs)])

def tyToWasmValtype(ty: ty) -> Literal['i64', 'i32']:
    match(ty):
        case Int():
            return 'i64'
        case Bool():
            return 'i32'

def compileStmts(stmts: list[stmt]) -> list[WasmInstr]:
    if len(stmts) > 0:
        stmt = stmts.pop(0)
        match(stmt):
            case StmtExp(exp):
                return compileExp(exp) + compileStmts(stmts)
            case Assign(id, exp):
                return compileExp(exp) + [WasmInstrVarLocal('set', identToWasmId(id))] + compileStmts(stmts)
            case IfStmt(cond, thenBody, elseBody):
                return compileExp(cond) + [WasmInstrIf(None, compileStmts(thenBody), compileStmts(elseBody))] + compileStmts(stmts)
            case WhileStmt(cond, body):
                global n
                loopExit = "$loop_exit_" + str(n)
                loopStart = "$loop_start_" + str(n)
                n += 1 
                loopCond = compileExp(cond) + [WasmInstrIf(None, [], [WasmInstrBranch(WasmId(loopExit), False)])]
                loop: list[WasmInstr] = [WasmInstrLoop(WasmId(loopStart), loopCond + compileStmts(body) + [WasmInstrBranch(WasmId(loopStart), False)])]   
                result: list[WasmInstr] = [WasmInstrBlock(WasmId(loopExit), None, loop)] + compileStmts(stmts)
                return result
            case _:
                raise Exception("Unknown statement: " + str(stmt))
    return []

n = 0

def compileExp(exp: exp) -> list[WasmInstr]:
    match exp:
        case IntConst(value):
            return [WasmInstrConst('i64', value)]
        case Name(id):
            return [WasmInstrVarLocal('get', identToWasmId(id, tyOfExp(exp)))]
        case Call(name, args):
            compiledArgs = [instr for arg in args for instr in compileExp(arg)]
            type = None
            if len(args) != 0:
                type = tyOfExp(args[0])
            compiledArgs.append(WasmInstrCall(identToWasmId(name, type)))
            return compiledArgs
        case UnOp(op, e):
            type = tyToWasmValtype(tyOfExp(e))
            match(op):
                case USub():
                    return compileExp(e) + [WasmInstrConst(type, -1)] + [WasmInstrNumBinOp(type, 'mul')]
                case Not():
                    assert(type == 'i32')
                    return compileExp(e) + [WasmInstrConst(type, 1)] + [WasmInstrNumBinOp(type, 'sub')]
        case BinOp(left, op, right):
            return compileBinOp(left, op, right)
        case BoolConst(value):
            return [WasmInstrConst('i32', 0 if not value else 1)]
        case _:
            raise Exception("Unknown expression")

def compileBinOp(left: exp, op: binaryop, right: exp) -> list[WasmInstr]:
    leftTy = tyOfExp(left)
    rightTy = tyOfExp(right)
    if leftTy != rightTy:
            raise Exception("Left and right type not equal")
    opLit = binOpToLiteral(op)
    match(opLit):
        case 'add' | 'mul' | 'sub':
            return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp(tyToWasmValtype(leftTy), opLit)]
        case 'and':
            return compileExp(left) + [WasmInstrIf('i32', compileExp(right), [WasmInstrConst('i32', 0)])]
        case 'or':
            return compileExp(left) + [WasmInstrIf('i32', [WasmInstrConst('i32', 1)], compileExp(right))]
        # case Eq() | NotEq() | Greater() | GreaterEq() | Less() | LessEq():
        case _:
            typeId = tyToWasmValtype(leftTy)
            return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp(typeId, opLit)]
        # case _:
        #     raise Exception("Unsupported binary op")


def identToWasmId(ident: ident, ty: Optional[ty]=None) -> WasmId:
    match ident.name:
        case 'print':
            assert(ty)
            typeId = tyToWasmValtype(ty)
            if typeId == 'i32':
                typeId = 'bool'
            return WasmId('$print_' + typeId)
        case 'input_int':
            return WasmId('$input_i64')
        case _:
            return WasmId('$' + ident.name)

def tyOfExp(e: exp) -> ty:
    if e.ty:
        match(e.ty):
            case NotVoid():
                return e.ty.ty
            case Void():
                raise Exception("Is void")
    raise Exception(str(e) + " has no type")

type binaryOpLiteral = Literal['add', 'sub', 'mul', 'lt_s', 'le_s', 'gt_s', 'ge_s', 'eq', 'ne', 'and', 'or']

def binOpToLiteral(op: binaryop) -> binaryOpLiteral:
    match op:
        case Add():
            return 'add'
        case Sub():
            return 'sub'
        case Mul():
            return 'mul'
        case Less():
            return 'lt_s'
        case LessEq():
            return 'le_s'
        case Greater():
            return 'gt_s'
        case GreaterEq():
            return 'ge_s'
        case Eq():
            return 'eq'
        case NotEq():
            return 'ne'
        case And():
            return 'and'
        case Or():
            return 'or'
        case _:
            raise Exception("Unknown binary operation")


            
    
    