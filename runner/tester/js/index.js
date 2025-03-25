const fs = require('fs');
const axios = require('axios');
const path = require('path');
const { execSync } = require('child_process');
const puppeteer = require('puppeteer');


function getJaegerNodePort() {
    try {
        const result = execSync(
            "kubectl get svc tracing -n istio-system -o jsonpath='{.spec.ports[?(@.name==\"http-query\")].nodePort}'"
        );
        return result.toString().trim();
    } catch (error) {
        console.error("Error executing kubectl command:", error);
        return null;
    }
}

function getServiceNameOfSpan(span) {
    let serviceName = 'unknown';
    if (span.tags) {
        for (const tag of span.tags) {
            if (tag.key === 'istio.canonical_service') {
                serviceName = tag.value;
                break;
            }
        }
    }
    if (serviceName === 'unknown') {
        serviceName = span.operationName.split(':')[0];
    }
    return serviceName;
}

function getPodNameOfSpan(span) {
    const IP_INDEX = 1;
    const POD_NAME_INDEX = 2;
    let podName = 'unknown';
    if (span.tags) {
        for (const tag of span.tags) {
            if (tag.key === 'node_id') {
                podName = tag.value.split('~')[POD_NAME_INDEX];
                break;
            }
        }
    }
    return podName;
}

async function fetchTraces() {
    const port = getJaegerNodePort();
    if (!port) return;

    const jaegerBaseUrl = `http://localhost:${port}/jaeger/api`;
    const serviceName = "frontend.default";
    const limit = 100;

    try {
        const response = await axios.get(`${jaegerBaseUrl}/traces?service=${serviceName}&limit=${limit}`);
        const traceData = response.data;

        if (!traceData.data || traceData.data.length === 0) {
            console.log("No traces found.");
            return;
        }

        let allTraces = [];
        for (const trace of traceData.data) {
            const traceId = trace.traceID;
            console.log(`Found trace ID: ${traceId}`);
            const traceResponse = await axios.get(`${jaegerBaseUrl}/traces/${traceId}`);
            allTraces.push(traceResponse.data);
        }

        fs.writeFileSync("trace_results.json", JSON.stringify(allTraces, null, 4));
        console.log(`Downloaded ${allTraces.length} traces.`);
    } catch (error) {
        console.error("Error fetching traces:", error);
    }
}

function processTraces() {
    const allowedServices = new Set(["frontend", "cartservice"]);
    const filePath = "trace_results.json";
    if (!fs.existsSync(filePath)) {
        console.log("Trace file not found.");
        return;
    }

    const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    let nodes = new Map();
    let links = [];

    for (const traceItem of data) {
        if (!traceItem.data) continue;

        for (const trace of traceItem.data) {
            const spans = new Map(trace.spans.map(span => [span.spanID, span]));
            for (const span of trace.spans) {
                const serviceName = getServiceNameOfSpan(span);
                const pod = getPodNameOfSpan(span);

                if (!allowedServices.has(serviceName)) continue;

                if (!nodes.has(pod)) {
                    nodes.set(pod, { name: pod, category: serviceName });
                }

                for (const ref of span.references || []) {
                    if (ref.refType === "CHILD_OF" && spans.has(ref.spanID)) {
                        const parentPod = getPodNameOfSpan(spans.get(ref.spanID));
                        if (allowedServices.has(getServiceNameOfSpan(spans.get(ref.spanID)))) {
                            links.push({ source: parentPod, target: pod, value: span.duration / 1e3 });
                        }
                    }
                }
            }
        }
    }

    const graphData = {
        nodes: Array.from(nodes.values()),
        links: links
    };

    fs.writeFileSync("graph_data.json", JSON.stringify(graphData, null, 4));
    console.log("Graph data saved to graph_data.json");
}

async function generateGraphImage() {
    const filePath = "graph_data.json";
    if (!fs.existsSync(filePath)) {
        console.log("Graph data file not found.");
        return;
    }

    const graphData = JSON.parse(fs.readFileSync(filePath, 'utf8'));

    const htmlContent = `
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.2/echarts.min.js"></script>
        <style> body { margin: 0; } </style>
    </head>
    <body>
        <div id="chart" style="width: 1200px; height: 800px;"></div>
        <script>
            var chart = echarts.init(document.getElementById('chart'));
            var option = {
                title: { text: 'Microservices Call Graph' },
                tooltip: {},
                series: [{
                    type: 'graph',
                    layout: 'force',
                    nodes: ${JSON.stringify(graphData.nodes)},
                    links: ${JSON.stringify(graphData.links)},
                    roam: true,
                    label: { show: true },
                    force: { repulsion: 200 }
                }]
            };
            chart.setOption(option);
        </script>
    </body>
    </html>`;

    // 启动 Puppeteer 生成截图
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    await page.setContent(htmlContent);
    await page.waitForSelector('#chart');

    // 截图并保存
    const outputFilePath = path.join(__dirname, 'fig', 'microservice_graph.png');
    await page.screenshot({ path: outputFilePath, fullPage: true });

    await browser.close();
    console.log(`Graph saved as ${outputFilePath}`);
}

async function main() {
    await fetchTraces();
    processTraces();
    await generateGraphImage();
}

main();
