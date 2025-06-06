from flask import Flask, jsonify, render_template, request
from pymodbus.client import ModbusSerialClient as ModbusClient
from datetime import datetime

app = Flask(__name__)

modbus_client = ModbusClient(
    method='rtu',
    port='COM3',
    baudrate=19200,
    parity='N',
    stopbits=2,
    bytesize=8,
    timeout=1
)

registers = {
    'Coil': {f'Coil_{i:03d}': i - 1 for i in range(1, 17)},
    'Status': {f'Status_{i:03d}': i - 1 for i in range(1, 13)},
    'Input': {f'Input_{i:03d}': i - 1 for i in range(1, 20, 2)},
    'Hold': {
        'Hold_001': 0, 'Hold_003': 2, 'Hold_005': 4, 'Hold_007': 6, 'Hold_009': 8,
        'Hold_011': 10, 'Hold_013': 12, 'Hold_015': 14, 'Hold_017': 16, 'Hold_019': 18,
        'Hold_021': 20, 'Hold_023': 22, 'Hold_031': 30, 'Hold_033': 32, 'Hold_035': 34,
        'Hold_037': 36, 'Hold_039': 38, 'Hold_041': 40, 'Hold_043': 42, 'Hold_045': 44,
        'Hold_047': 46, 'Hold_049': 48, 'Hold_051': 50, 'Hold_053': 52, 'Hold_055': 54,
        'Hold_057': 56, 'Hold_059': 58, 'Hold_061': 60
    }
}

@app.route('/')
def index():
    return render_template('index.html', groups=registers)

@app.route('/data')
def get_data():
    if not modbus_client.connect():
        return jsonify({'timestamp': '--', 'values': {k: '连接失败' for t in registers.values() for k in t}})

    all_values = {}
    for reg_type, items in registers.items():
        for name, addr in items.items():
            try:
                if reg_type == 'Coil':
                    result = modbus_client.read_coils(address=addr, count=1, unit=1)
                elif reg_type == 'Status':
                    result = modbus_client.read_discrete_inputs(address=addr, count=1, unit=1)
                elif reg_type == 'Input':
                    result = modbus_client.read_input_registers(address=addr, count=1, unit=1)
                elif reg_type == 'Hold':
                    result = modbus_client.read_holding_registers(address=addr, count=1, unit=1)
                else:
                    result = None
                all_values[name] = result.bits[0] if hasattr(result, 'bits') else (result.registers[0] if hasattr(result, 'registers') else '错误')
            except:
                all_values[name] = '错误'

    return jsonify({'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'values': all_values})

@app.route('/write', methods=['POST'])
def write_value():
    reg_name = request.form.get('reg_name')
    value = request.form.get('value')

    if not reg_name or value is None:
        return '无效输入', 400

    try:
        value = int(value)
        if reg_name.startswith('Coil'):
            addr = registers['Coil'].get(reg_name)
            result = modbus_client.write_coil(addr, bool(value), unit=1)
        elif reg_name.startswith('Hold'):
            addr = registers['Hold'].get(reg_name)
            result = modbus_client.write_register(addr, value, unit=1)
        else:
            return '只能写入 Coil 或 Hold 类型', 400

        return '写入成功' if result.isError() is False else '写入失败', 200
    except:
        return '写入异常', 500

if __name__ == '__main__':
    print("🚀 启动 Flask Modbus 多类型监控与写入...")
    app.run(host='0.0.0.0', port=10000)

@app.route('/write_value', methods=['POST'])
def write_value():
    data = request.get_json()
    reg_id = data.get('id')
    value = data.get('value')

    # 仅支持 Coil 和 Hold
    try:
        if reg_id.startswith('Coil_') and reg_id in registers['Coil']:
            address = registers['Coil'][reg_id]
            val = True if value == 'true' else False
            result = modbus_client.write_coil(address, val)
            return f"Coil 寄存器 {reg_id} 写入 {'成功' if result.isError() is False else '失败'}"
        elif reg_id.startswith('Hold_') and reg_id in registers['Hold']:
            address = registers['Hold'][reg_id]
            val = 1 if value == 'true' else 0
            result = modbus_client.write_register(address, val)
            return f"Hold 寄存器 {reg_id} 写入 {'成功' if result.isError() is False else '失败'}"
        else:
            return "不支持的寄存器或名称错误", 400
    except Exception as e:
        return f"写入时发生错误: {str(e)}", 500
