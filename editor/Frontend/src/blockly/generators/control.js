import { pythonGenerator } from 'blockly/python';

export const defineControlGenerators = () => {
  pythonGenerator.forBlock['control_run_project_script'] = function (block) {
    const scriptPath = String(block.getFieldValue('PATH') || '').trim();
    return `CoronaEngine.run_project_script(${JSON.stringify(scriptPath)})\n`;
  };

  pythonGenerator.forBlock['control_wait'] = function (block) {
    const seconds = block.getFieldValue('SECONDS');
    return `CoronaEngine.wait(${seconds})\n`;
  };

  /** Inject a stop guard and optionally yield once per frame for long-running loops. */
  function injectStopCheck(branch, indent, paced = false) {
    let guard = indent + 'CoronaEngine.check_stop()\n';
    if (paced) guard += indent + 'CoronaEngine.loop_yield()\n';
    if (!branch) return guard + indent + 'pass\n';
    return guard + branch;
  }

  pythonGenerator.forBlock['control_for'] = function (block) {
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (pythonGenerator.STATEMENT_PREFIX) {
      branch =
        pythonGenerator.prefixLines(
          pythonGenerator.STATEMENT_PREFIX.replace(/%1/g, "'" + block.id + "'"),
          pythonGenerator.INDENT
        ) + branch;
    }
    branch = injectStopCheck(branch, pythonGenerator.INDENT, true);
    return `while True:\n` + branch;
  };

  // 定义重复执行 x 次积木块的 Python 代码生成器
  pythonGenerator.forBlock['control_forX'] = function (block) {
    const times =
      pythonGenerator.valueToCode(block, 'TIMES', pythonGenerator.ORDER_NONE) ||
      block.getFieldValue('DEFAULT_TIMES');
    let branch = pythonGenerator.statementToCode(block, 'DO');
    branch = injectStopCheck(branch, pythonGenerator.INDENT);
    return `for _ in range(${times}):\n` + branch;
  };

  pythonGenerator.forBlock['control_if'] = function (block) {
    const condition =
      pythonGenerator.valueToCode(block, 'CONDITION', pythonGenerator.ORDER_NONE) || 'False';
    let branch = pythonGenerator.statementToCode(block, 'DO');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    return `if ${condition}:\n` + branch;
  };

  // 定义如果那么否则积木块的 Python 代码生成器
  pythonGenerator.forBlock['control_else'] = function (block) {
    const condition =
      pythonGenerator.valueToCode(block, 'CONDITION', pythonGenerator.ORDER_NONE) || 'False';
    let branch = pythonGenerator.statementToCode(block, 'DO');
    let elseBranch = pythonGenerator.statementToCode(block, 'ELSE');
    if (!branch) branch = pythonGenerator.INDENT + 'pass\n';
    let code = `if ${condition}:\n` + branch;
    if (elseBranch !== null) {
      // If else exists but is empty, still output a pass.
      if (!elseBranch) elseBranch = pythonGenerator.INDENT + 'pass\n';
      code += `else:\n` + elseBranch;
    }
    return code;
  };

  // 定义等待直到条件满足积木块的 Python 代码生成器
  pythonGenerator.forBlock['control_wait2'] = function (block) {
    const condition =
      pythonGenerator.valueToCode(block, 'CONDITION', pythonGenerator.ORDER_NONE) || 'False';
    // 等待直到 + stop 检查 + 短休眠防止 CPU 空转
    const body =
      pythonGenerator.INDENT + 'CoronaEngine.check_stop()\n' +
      pythonGenerator.INDENT + 'CoronaEngine.wait(0.05)\n';
    return `while not (${condition}):\n` + body;
  };

  // 定义重复执行直到积木块的 Python 代码生成器
  pythonGenerator.forBlock['control_until'] = function (block) {
    const condition =
      pythonGenerator.valueToCode(block, 'CONDITION', pythonGenerator.ORDER_NONE) || 'False';
    let branch = pythonGenerator.statementToCode(block, 'DO');
    branch = injectStopCheck(branch, pythonGenerator.INDENT, true);
    return `while not (${condition}):\n` + branch;
  };

  // 定义停止积木块的 Python 代码生成器
  pythonGenerator.forBlock['control_stop'] = function (block) {
    const stopOption = block.getFieldValue('STOP_OPTION');
    return `CoronaEngine.stop("${stopOption}")\n`;
  };

  pythonGenerator.forBlock['control_cloneStart'] = function () {
    return `CoronaEngine.cloneStart()\n`;
  };

  pythonGenerator.forBlock['control_clone'] = function (block) {
    const x = String(block.getFieldValue('x') || '');
    return `CoronaEngine.clone(${JSON.stringify(x)})\n`;
  };

  pythonGenerator.forBlock['control_cloneDEL'] = function () {
    return `CoronaEngine.deleteClone()\n`;
  };

  pythonGenerator.forBlock['control_senceSet'] = function (block) {
    const x = block.getFieldValue('x');
    return `CoronaEngine.setScene("${x}")\n`;
  };

  pythonGenerator.forBlock['control_nextSence'] = function () {
    return `CoronaEngine.nextScene()\n`;
  };

  pythonGenerator.forBlock['control_restart_level'] = function () {
    return 'CoronaEngine.restart_level()\n';
  };


  pythonGenerator.forBlock.control_cooldown_ready = (block) => {
    const name = pythonGenerator.valueToCode(block, 'NAME', pythonGenerator.ORDER_NONE) || "''";
    const seconds = pythonGenerator.valueToCode(block, 'SECONDS', pythonGenerator.ORDER_NONE) || block.getFieldValue('SECONDS_NUMBER') || '0';
    const consume = block.getFieldValue('CONSUME') === 'TRUE' ? 'True' : 'False';
    return [`CoronaEngine.cooldown_ready(${name}, ${seconds}, ${consume})`, pythonGenerator.ORDER_FUNCTION_CALL];
  };
  pythonGenerator.forBlock.control_reset_cooldown = (block) => `CoronaEngine.reset_cooldown(${pythonGenerator.valueToCode(block, 'NAME', pythonGenerator.ORDER_NONE) || "''"})\n`;
  pythonGenerator.forBlock.control_start_cooldown = (block) => {
    const name = pythonGenerator.valueToCode(block, 'NAME', pythonGenerator.ORDER_NONE) || "''";
    const seconds = pythonGenerator.valueToCode(block, 'SECONDS', pythonGenerator.ORDER_NONE) || block.getFieldValue('SECONDS_NUMBER') || '0';
    return `CoronaEngine.start_cooldown(${name}, ${seconds})\n`;
  };

};
