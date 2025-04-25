const express = require('express');
const promClient = require('prom-client');
const app = express();
const port = process.env.PORT || 8080;

// 创建prometheus指标
const register = new promClient.Registry();
const requestDuration = new promClient.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5],
  registers: [register]
});

const requestCounter = new promClient.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['status_code'],
  registers: [register]
});

// 默认CPU负载级别
const DEFAULT_LOAD = 100000;

// CPU密集型操作
function computeIntensive(iterations) {
  const start = process.hrtime();

  let result = 0;

  for (let i = 0; i < iterations; i++) {
    // 多重数学计算
    const x = Math.sin(i) * Math.cos(i * 0.5) * Math.tan(i * 0.2 + 0.1);
    const y = Math.sqrt(Math.abs(x)) * Math.log(i + 1);
    const z = Math.pow(y, 1.5) / (Math.exp(-x) + 1e-9); // 加1e-9避免除以0

    // 嵌套循环增加复杂度
    for (let j = 0; j < 3; j++) {
      result += Math.sin(z + Math.random() * j);
    }
  }

  const end = process.hrtime(start);
  const duration = (end[0] * 1e9 + end[1]) / 1e9; // 秒

  return { result, duration };
}

// 健康检查端点
app.get('/health', (req, res) => {
  res.status(200).send('OK');
});

// 测试端点
app.get('/test', (req, res) => {
  const endTimer = requestDuration.startTimer();
  try {
    // 从查询参数获取负载级别，默认为固定值
    const intensity = parseInt(req.query.intensity) || DEFAULT_LOAD;
    
    // 执行CPU密集型操作
    const { result, duration } = computeIntensive(intensity);
    
    // 记录请求成功
    requestCounter.inc({ status_code: 200 });
    endTimer();
    
    res.json({ 
      result, 
      computationTime: duration,
      serverTime: new Date().toISOString(),
      podName: process.env.POD_NAME || 'unknown'
    });
  } catch (error) {
    // 记录请求失败
    requestCounter.inc({ status_code: 500 });
    endTimer();
    res.status(500).json({ error: error.message });
  }
});

// Prometheus指标端点
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// 启动服务器
app.listen(port, () => {
  console.log(`测试服务运行在端口 ${port}`);
});
