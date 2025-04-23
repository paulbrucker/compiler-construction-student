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

def tyToWasmValtype(ty) -> WasmValtype:
    match(ty):
        case Int():
            return 'i64'
        case Bool():
            return 'i32'
        case _:
            raise Exception("Type " + ty + "Not implemented")

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
                loop = [WasmInstrLoop(WasmId(loopStart), loopCond + compileStmts(body) + [WasmInstrBranch(WasmId(loopStart), False)])]   
                return [WasmInstrBlock(WasmId(loopExit), None, loop)] + compileStmts(stmts)
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
            compiledArgs.append(WasmInstrCall(identToWasmId(name, None if len(args) == 0 else tyOfExp(args[0]))))
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
    match(op):
        case Add() | Mul() | Sub():
            return compileExp(left) + compileExp(right) + [WasmInstrNumBinOp(tyToWasmValtype(leftTy), binOpToLiteral(op))]
        case And():
            return compileExp(left) + [WasmInstrIf('i32', compileExp(right), [WasmInstrConst('i32', 0)])]
        case Or():
            return compileExp(left) + [WasmInstrIf('i32', [WasmInstrConst('i32', 1)], compileExp(right))]
        case Eq() | NotEq() | Greater() | GreaterEq() | Less() | LessEq():
            typeId = tyToWasmValtype(leftTy)
            return compileExp(left) + compileExp(right) + [WasmInstrIntRelOp(typeId, binOpToLiteral(op))]
        case _:
            raise Exception("Unsupported binary op")


def identToWasmId(ident: ident, ty: ty=None) -> WasmId:
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
    ty = e.ty
    if not ty or ty == Void:
        raise Exception(str(e) + " has no type")
    return ty.ty

def binOpToLiteral(op: binaryop):
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


            
    
    