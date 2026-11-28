
"use strict";

const DATA = JSON.parse(
    document.getElementById("decisioniq-data").textContent
);

const $ = id => document.getElementById(id);

const PALETTE = [
    "#122B49", "#285784", "#57799E",
    "#8CA5BF", "#B8CADD", "#DCE4ED"
];

const NAV = [
    ["Workspace", [
        ["overview", "Overview", "layout-dashboard"],
        ["explorer", "Dataset Explorer", "database"]
    ]],
    ["Data Intelligence", [
        ["structural", "Data Structure", "columns-3"],
        ["statistical", "Statistics", "chart-no-axes-column"],
        ["missing_values", "Missing Values", "shield-check"],
        ["outliers", "Outlier Intelligence", "activity"]
    ]],
    ["Advanced Analytics", [
        ["relationships", "Relationships", "network"],
        ["temporal", "Temporal Analysis", "calendar-days"],
        ["multicollinearity", "Multicollinearity", "git-merge"]
    ]],
    ["System", [
        ["benchmark", "Performance", "gauge"],
        ["information", "Report Information", "file-text"]
    ]]
];

const pages = Object.fromEntries(
    NAV.flatMap(([group, items]) =>
        items.map(([key, title, icon]) =>
            [key, {title, icon, group}]
        )
    )
);

const state = {
    industry: DATA.reports.manufacturing
        ? "manufacturing"
        : Object.keys(DATA.reports)[0],
    page: "overview",
    filters: {},
    tables: {}
};

let charts = [];
let currentExport = [];
let renderVersion = 0;

function report() {
    return DATA.reports[state.industry];
}

function moduleResult(name) {
    return report().modules?.[name]?.result || {};
}

function esc(value) {
    return String(value ?? "—")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function fmt(value, digits = 4) {

    if (value === null || value === undefined)
        return "—";

    if (typeof value === "number") {

        if (!Number.isFinite(value))
            return "—";

        if (value !== 0 && Math.abs(value) < 0.0001)
            return value.toExponential(3);

        return value.toLocaleString(undefined, {
            maximumFractionDigits: digits
        });
    }

    if (typeof value === "object")
        return JSON.stringify(value);

    return String(value);
}

function label(value) {
    return String(value ?? "")
        .replaceAll("_", " ")
        .replace(/\b\w/g, c => c.toUpperCase());
}

function icons() {
    if (window.lucide)
        lucide.createIcons();
}

function finite(value) {
    return typeof value === "number"
        && Number.isFinite(value);
}

function pct(value) {
    return finite(value) ? fmt(value, 2) + "%" : "—";
}

function filters() {
    const key = `${state.industry}:${state.page}`;
    return state.filters[key] ||= {};
}

function setFilter(key, value) {
    filters()[key] = value;
    state.tables = {};
    render();
}

function go(page) {
    state.page = page;
    state.tables = {};
    render();
}

function empty(message = "No applicable analytical results.") {
    return `<div class="empty">${esc(message)}</div>`;
}

function notice(message) {
    return `<div class="notice">${esc(message)}</div>`;
}

function status(value) {

    const text = String(value ?? "unavailable");

    const cls = [
        "completed", "passed", "complete", "low"
    ].includes(text.toLowerCase())
        ? "good"
        : [
            "failed", "critical", "perfect_collinearity"
        ].includes(text.toLowerCase())
            ? "bad"
            : [
                "warning", "partial_success",
                "review_required"
            ].includes(text.toLowerCase())
                ? "warn"
                : "";

    return `<span class="status ${cls}">
        ${esc(label(text))}
    </span>`;
}

function panel(title, content, span = 12, subtitle = "") {

    return `
        <section class="glass panel span-${span}">
            <div class="panel-header">
                <div>
                    <h2>${esc(title)}</h2>
                    ${subtitle
                        ? `<div class="muted">${esc(subtitle)}</div>`
                        : ""}
                </div>
            </div>
            ${content}
        </section>
    `;
}

function kpi(title, value, icon, target = "", span = 3) {

    const tag = target ? "button" : "div";

    return `
        <${tag} class="glass kpi span-${span}"
                ${target ? `data-go="${esc(target)}"` : ""}>
            <div class="spread">
                <span class="muted">${esc(title)}</span>
                <span class="kpi-icon">
                    <i data-lucide="${esc(icon)}"></i>
                </span>
            </div>
            <div class="metric">${esc(fmt(value))}</div>
        </${tag}>
    `;
}

function grid(content) {
    return `<div class="grid">${content}</div>`;
}

function raw(value) {
    return `<details>
        <summary>Inspect complete analytical output</summary>
        <pre>${esc(JSON.stringify(value, null, 2))}</pre>
    </details>`;
}

function selectControl(key, options, value, title) {

    return `<label class="muted">
        ${esc(title)}
        <select class="control" data-filter="${esc(key)}">
            ${options.map(item => {
                const opt = typeof item === "object"
                    ? item
                    : {value:item, label:label(item)};

                return `<option value="${esc(opt.value)}"
                    ${String(opt.value) === String(value)
                        ? "selected" : ""}>
                    ${esc(opt.label)}
                </option>`;
            }).join("")}
        </select>
    </label>`;
}

function searchControl(value = "") {
    return `<input class="control"
        data-filter="search"
        value="${esc(value)}"
        placeholder="Search columns..."
        aria-label="Search columns">`;
}

function matches(row, query) {
    return JSON.stringify(row)
        .toLowerCase()
        .includes(String(query || "").toLowerCase());
}

function openDrawer(title, value) {

    $("drawer-title").textContent = title;

    $("drawer-content").innerHTML =
        `<pre>${esc(JSON.stringify(value, null, 2))}</pre>`;

    $("drawer").classList.add("open");
    $("overlay").classList.add("open");
    $("close-drawer").focus();
}

function closeDrawer() {
    $("drawer").classList.remove("open");
    $("overlay").classList.remove("open");
}

function columnDetails(name) {

    const details = {};

    for (const key of [
        "structural", "statistical",
        "missing_values", "outliers",
        "multicollinearity"
    ]) {
        const row = moduleResult(key).columns
            ?.find(c => c.column_name === name);

        if (row)
            details[key] = row;
    }

    openDrawer(name, details);
}

function download(content, filename, type) {

    const url = URL.createObjectURL(
        new Blob([content], {type})
    );

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function csvCell(value) {

    let text = value == null ? "" : fmt(value, 12);

    // Protect spreadsheet users from formula injection.
    if (typeof value === "string"
        && /^[=+\-@\t\r]/.test(text)) {
        text = "'" + text;
    }

    return '"' + text.replaceAll('"', '""') + '"';
}

function exportCSV(rows) {

    if (!rows.length)
        return;

    const keys = [...new Set(rows.flatMap(Object.keys))];

    const csv = [
        keys.map(csvCell).join(","),
        ...rows.map(row =>
            keys.map(key => csvCell(row[key])).join(",")
        )
    ].join("\n");

    download(
        csv,
        `decisioniq_${state.industry}_${state.page}.csv`,
        "text/csv;charset=utf-8"
    );
}

function table(id, rows, columns, onClick = null) {

    const version = renderVersion;

    if (!rows.length)
        return empty();

    const t = state.tables[id] ||= {
        page: 0,
        size: 10,
        sort: null,
        ascending: true
    };

    const sorted = [...rows];

    if (t.sort) {
        sorted.sort((a,b) => {

            const x = a[t.sort];
            const y = b[t.sort];

            if (x == null) return y == null ? 0 : 1;
            if (y == null) return -1;

            const cmp = finite(x) && finite(y)
                ? x - y
                : String(x).localeCompare(String(y));

            return t.ascending ? cmp : -cmp;
        });
    }

    const totalPages = Math.ceil(sorted.length / t.size);

    t.page = Math.min(t.page, totalPages - 1);

    const visible = sorted.slice(
        t.page * t.size,
        (t.page + 1) * t.size
    );

    currentExport = sorted;

    queueMicrotask(() => {

        if (version !== renderVersion)
            return;

        const root = $(id);
        if (!root) return;

        root.querySelectorAll("th[data-key]")
            .forEach(th => {

                th.onclick = () => {

                    const key = th.dataset.key;

                    t.ascending = t.sort === key
                        ? !t.ascending : true;

                    t.sort = key;
                    t.page = 0;
                    render();
                };
            });

        root.querySelectorAll("tr[data-index]")
            .forEach(tr => {

                tr.onclick = () => {

                    const row = visible[
                        Number(tr.dataset.index)
                    ];

                    if (onClick)
                        onClick(row);
                    else
                        openDrawer("Analytical details", row);
                };
            });

        root.querySelector("[data-prev]").onclick = () => {
            t.page = Math.max(0, t.page - 1);
            render();
        };

        root.querySelector("[data-next]").onclick = () => {
            t.page = Math.min(totalPages - 1, t.page + 1);
            render();
        };

        root.querySelector("[data-csv]").onclick = () =>
            exportCSV(sorted);
    });

    return `
        <div id="${esc(id)}">
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            ${columns.map(key => `
                                <th data-key="${esc(key)}">
                                    ${esc(label(key))}
                                    ${t.sort === key
                                        ? t.ascending ? " ↑" : " ↓"
                                        : ""}
                                </th>
                            `).join("")}
                        </tr>
                    </thead>
                    <tbody>
                        ${visible.map((row,i) => `
                            <tr data-index="${i}">
                                ${columns.map(key => `
                                    <td>${esc(fmt(row[key]))}</td>
                                `).join("")}
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>

            <div class="toolbar spread">
                <span class="muted">
                    ${sorted.length} results ·
                    Page ${t.page + 1} of ${totalPages}
                </span>
                <div class="flex">
                    <button class="control" data-csv>
                        Export CSV
                    </button>
                    <button class="icon-btn" data-prev
                        aria-label="Previous page"
                        ${t.page === 0 ? "disabled" : ""}>
                        <i data-lucide="chevron-left"></i>
                    </button>
                    <button class="icon-btn" data-next
                        aria-label="Next page"
                        ${t.page >= totalPages - 1
                            ? "disabled" : ""}>
                        <i data-lucide="chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
    `;
}

function chart(id, options, onClick = null, tall = false) {

    const version = renderVersion;

    queueMicrotask(() => {

        if (version !== renderVersion)
            return;

        const element = $(id);

        if (!element)
            return;

        const instance = echarts.init(element);

        instance.setOption({
            color: PALETTE,
            textStyle: {
                fontFamily: "Segoe UI, sans-serif",
                color: "#122B49",
                fontSize: 11
            },
            animationDuration: 350,
            tooltip: {
                trigger: "item",
                confine: true,
                backgroundColor: "#F8FAFC",
                borderColor: "#DCE4ED",
                textStyle: {color:"#122B49"}
            },
            toolbox: {
                right: 10,
                feature: {
                    saveAsImage: {
                        name: `DecisionIQ_${id}`,
                        pixelRatio: 2
                    }
                }
            },
            ...options
        });

        if (onClick)
            instance.on("click", onClick);

        charts.push(instance);
    });

    return `<div id="${esc(id)}"
        class="chart ${tall ? "tall" : ""}"></div>`;
}

function bars(id, rows, nameKey, valueKey,
              onClick = null, unit = "") {

    const data = rows.filter(r => finite(r[valueKey]));

    if (!data.length)
        return empty("No measured values available.");

    return chart(id, {
        grid: {
            left: 12,
            right: 40,
            top: 35,
            bottom: 15,
            containLabel: true
        },
        xAxis: {
            type: "value",
            name: unit,
            splitLine: {
                lineStyle: {color:"#DCE4ED"}
            }
        },
        yAxis: {
            type: "category",
            inverse: true,
            data: data.map(r => r[nameKey]),
            axisLabel: {
                width: 160,
                overflow: "truncate"
            }
        },
        series: [{
            type: "bar",
            data: data.map(r => r[valueKey]),
            barMaxWidth: 22,
            itemStyle: {
                borderRadius: 4
            },
            emphasis: {focus:"self"}
        }]
    }, p => {
        if (onClick)
            onClick(data[p.dataIndex]);
        else
            openDrawer("Chart details", data[p.dataIndex]);
    }, data.length > 10);
}

function overview() {

    const r = report();
    const d = r.dataset;
    const q = r.quality_indicators;
    const e = r.execution;

    const cols = moduleResult("structural").columns || [];
    const missing = moduleResult("missing_values").columns || [];

    const types = {};

    cols.forEach(c => {
        const type = c.detected_type || "unknown";
        types[type] = (types[type] || 0) + 1;
    });

    const engines = Object.entries(r.modules).map(
        ([name,m]) => ({
            module: label(name),
            status: m.status,
            seconds: m.execution_seconds
        })
    );

    const relationships = (
        moduleResult("relationships").numeric_relationships || []
    ).filter(x => x.method === "pearson")
        .sort((a,b) =>
            Math.abs(b.coefficient) - Math.abs(a.coefficient)
        ).slice(0,5);

    const findings = [];

    findings.push({
        title: "Dataset completeness",
        text: `${fmt(q.missing_cells)} cells are missing. `
            + "Investigate missingness in business-critical "
            + "fields before downstream modelling."
    });

    findings.push({
        title: "Duplicate records",
        text: `${fmt(q.duplicate_rows)} exact duplicate rows `
            + "were identified. Confirm the intended record "
            + "grain before removing duplicates."
    });

    if (relationships.length) {

        const p = relationships[0];

        findings.push({
            title: "Strongest observed Pearson association",
            text: `${p.column_a} and ${p.column_b}: `
                + `r = ${fmt(p.coefficient)}. `
                + "Investigate shared drivers and feature "
                + "redundancy. Association is not causation."
        });
    }

    return grid(
        kpi("Total records", d.row_count,
            "database", "explorer") +
        kpi("Attributes", d.column_count,
            "columns-3", "structural") +
        kpi("Completeness", pct(q.completeness_percentage),
            "shield-check", "missing_values") +
        kpi("Duplicate rows", q.duplicate_rows,
            "copy", "structural")
    ) + grid(
        panel("Column composition",
            chart("type-chart", {
                legend: {bottom:0},
                series: [{
                    type:"pie",
                    radius:["48%","72%"],
                    center:["50%","45%"],
                    data:Object.entries(types).map(
                        ([name,value]) => ({name,value})
                    ),
                    label:{show:false}
                }]
            }, () => go("structural")), 5) +

        panel("Profiling engine performance",
            bars("engine-chart", engines,
                "module", "seconds", null, "s"), 7)
    ) + grid(
        panel("Missing-value distribution",
            bars("overview-missing",
                missing.filter(c => c.missing_count > 0)
                    .sort((a,b) =>
                        b.missing_count - a.missing_count
                    ).slice(0,10),
                "column_name", "missing_percentage",
                row => columnDetails(row.column_name), "%"),
            6) +

        panel("Analytical findings",
            findings.map(f => `
                <div class="insight">
                    <strong>${esc(f.title)}</strong>
                    <div class="muted">${esc(f.text)}</div>
                </div>
            `).join(""), 6)
    ) + panel(
        "Execution status",
        `<div class="spread">
            ${status(r.status)}
            <span class="muted">
                ${e.completed_modules}/${e.total_modules}
                engines completed ·
                ${fmt(e.total_seconds)} seconds
            </span>
        </div>` +
        table("engine-table", engines,
            ["module","status","seconds"]) +
        notice("Execution success does not guarantee analytical "
            + "applicability or business data validity.")
    );
}

function explorer() {

    const f = filters();

    const columns = moduleResult("structural").columns || [];

    const types = [
        "all",
        ...new Set(columns.map(c => c.detected_type))
    ];

    const rows = columns.filter(c =>
        matches(c, f.search)
        && (!f.type || f.type === "all"
            || c.detected_type === f.type)
        && (!f.missing || f.missing === "all"
            || c.missing_count > 0)
        && (!f.key || f.key === "all"
            || c.candidate_key)
    );

    return panel("Column explorer", `
        <div class="toolbar">
            ${searchControl(f.search)}
            ${selectControl("type", types,
                f.type || "all", "Data type")}
            ${selectControl("missing", [
                {value:"all",label:"All columns"},
                {value:"missing",label:"Has missing values"}
            ], f.missing || "all", "Missingness")}
            ${selectControl("key", [
                {value:"all",label:"All columns"},
                {value:"keys",label:"Candidate keys"}
            ], f.key || "all", "Key status")}
        </div>
    ` + table("explorer-table", rows, [
        "column_name",
        "physical_dtype",
        "detected_type",
        "missing_percentage",
        "unique_count",
        "candidate_key"
    ], row => columnDetails(row.column_name)));
}

function structural() {

    const r = moduleResult("structural");

    return explorer() + grid(
        panel("Candidate keys",
            raw(r.candidate_keys || []), 4) +
        panel("Constant columns",
            raw(r.constant_columns || []), 4) +
        panel("Empty columns",
            raw(r.empty_columns || []), 4)
    );
}

function statistical() {

    const r = moduleResult("statistical");
    const f = filters();

    const columns = (r.columns || [])
        .filter(c => c.central_tendency);

    if (!columns.length)
        return empty("No numerical summaries available.");

    const selected = columns.find(
        c => c.column_name === f.variable
    ) || columns[0];

    const p = selected.position || {};
    const d = selected.dispersion || {};
    const c = selected.central_tendency || {};
    const dist = selected.distribution || {};

    const five = [
        p.min, p.q1, p.q2 ?? c.median, p.q3, p.max
    ];

    const percentiles = Object.entries(
        selected.percentiles || {}
    ).map(([key,value]) => ({
        percentile: Number(key),
        value
    })).filter(x =>
        finite(x.percentile) && finite(x.value)
    ).sort((a,b) => a.percentile - b.percentile);

    const boxPlot = five.every(finite)
        ? chart("boxplot", {
            grid: {
                left:45, right:30, top:40, bottom:45
            },
            xAxis: {
                type:"category",
                data:[selected.column_name]
            },
            yAxis:{type:"value",scale:true},
            series:[{
                type:"boxplot",
                data:[five],
                itemStyle:{
                    color:"#B8CADD",
                    borderColor:"#285784"
                }
            }]
        })
        : empty("Five-number summary unavailable.");

    const percentileChart = percentiles.length
        ? chart("percentile-chart", {
            tooltip:{trigger:"axis"},
            grid:{
                left:55,right:30,top:40,bottom:45
            },
            xAxis:{
                type:"value",
                min:0,max:100,
                name:"Percentile"
            },
            yAxis:{type:"value",scale:true},
            series:[{
                type:"line",
                data:percentiles.map(x => [
                    x.percentile <= 1
                        ? x.percentile * 100
                        : x.percentile,
                    x.value
                ]),
                symbolSize:7,
                lineStyle:{width:3},
                areaStyle:{opacity:.08}
            }]
        })
        : empty("Percentiles unavailable.");

    return panel("Variable selection",
        selectControl(
            "variable",
            columns.map(x => ({
                value:x.column_name,
                label:x.column_name
            })),
            selected.column_name,
            "Numerical variable"
        )
    ) + grid(
        kpi("Mean", c.mean, "chart-no-axes-column") +
        kpi("Median", c.median, "align-center") +
        kpi("Standard deviation",
            d.standard_deviation ?? d.std, "activity") +
        kpi("Skewness", dist.skewness, "chart-spline")
    ) + grid(
        panel("Five-number summary", boxPlot +
            notice("Whiskers show the reported minimum and "
                + "maximum, not Tukey outlier fences."), 6) +
        panel("Percentile curve", percentileChart, 6)
    ) + panel(
        "Distribution diagnostics",
        raw(selected) +
        notice("Histogram bins and raw observations are not "
            + "available in this summary report.")
    );
}

function missing() {

    const r = moduleResult("missing_values");
    const f = filters();
    const s = r.summary || {};

    const rows = (r.columns || []).filter(c =>
        matches(c,f.search)
        && (!f.severity || f.severity === "all"
            || c.severity === f.severity)
    ).sort((a,b) =>
        b.missing_percentage - a.missing_percentage
    );

    const patterns =
        r.missingness_patterns?.top_co_missing_patterns || [];

    return grid(
        kpi("Missing cells",s.missing_cells,"shield-alert") +
        kpi("Affected columns",s.affected_columns,"columns-3") +
        kpi("Incomplete rows",s.incomplete_rows,"list-filter") +
        kpi("Completeness",pct(s.completeness_percentage),
            "shield-check")
    ) + panel("Missingness explorer", `
        <div class="toolbar">
            ${searchControl(f.search)}
            ${selectControl("severity", [
                "all","complete","low",
                "warning","critical","empty"
            ], f.severity || "all", "Severity")}
        </div>
    ` + bars("missing-chart",rows,
        "column_name","missing_percentage",
        row => columnDetails(row.column_name),"%")
    ) + panel("Column-level findings",
        table("missing-table",rows,[
            "column_name","missing_count",
            "missing_percentage","severity",
            "business_critical","recommended_action"
        ],row => columnDetails(row.column_name))
    ) + panel("Co-missing patterns",
        patterns.length
            ? table("pattern-table",patterns,
                Object.keys(patterns[0]))
            : empty("No co-missing patterns reported.")
    );
}

function outliers() {

    const r = moduleResult("outliers");
    const f = filters();

    const method = f.method || "iqr";

    const rows = (r.columns || [])
        .filter(c => matches(c,f.search))
        .map(c => {

            const m = c.methods?.[method];

            return {
                column_name:c.column_name,
                status:method === "consensus"
                    ? c.agreement?.consensus_available
                        ? "evaluated" : "unavailable"
                    : m?.status ?? c.status,
                count:method === "consensus"
                    ? c.agreement?.consensus_outlier_count
                    : m?.outlier_count,
                percentage:method === "consensus"
                    ? c.agreement?.consensus_outlier_percentage
                    : m?.outlier_percentage
            };
        });

    return panel("Detection method",`
        <div class="toolbar">
            ${searchControl(f.search)}
            ${selectControl("method",[
                {value:"iqr",label:"Interquartile range"},
                {value:"zscore",label:"Z-score"},
                {value:"modified_zscore",label:"Modified Z-score"},
                {value:"consensus",label:"Consensus"}
            ],method,"Method")}
        </div>
    ` + notice("Outliers are investigation candidates, "
        + "not automatically invalid records.")
    ) + grid(
        panel("Detected observations",
            bars("outlier-count",rows,
                "column_name","count",
                row => columnDetails(row.column_name)),6) +
        panel("Flagged percentage",
            bars("outlier-percent",rows,
                "column_name","percentage",
                row => columnDetails(row.column_name),"%"),6)
    ) + panel("Detection details",
        table("outlier-table",rows,[
            "column_name","status","count","percentage"
        ],row => columnDetails(row.column_name))
    );
}

function relationships() {

    const r = moduleResult("relationships");
    const f = filters();

    const method = f.method || "pearson";
    const threshold = Number(f.threshold ?? 0);

    const all = (r.numeric_relationships || [])
        .filter(x => x.method === method);

    const rows = all.filter(x =>
        matches(x,f.search)
        && Math.abs(x.coefficient) >= threshold
        && (!f.direction || f.direction === "all"
            || (f.direction === "positive"
                ? x.coefficient > 0
                : x.coefficient < 0))
    ).sort((a,b) =>
        Math.abs(b.coefficient) - Math.abs(a.coefficient)
    );

    const names = [...new Set(
        rows.flatMap(x => [x.column_a,x.column_b])
    )];

    const cells = [];

    rows.forEach(row => {

        const a = names.indexOf(row.column_a);
        const b = names.indexOf(row.column_b);

        cells.push({
            value:[a,b,row.coefficient],
            relationship:row
        });

        cells.push({
            value:[b,a,row.coefficient],
            relationship:row
        });
    });

    const heatmap = names.length
        ? chart("heatmap",{
            grid:{
                left:145,right:35,top:45,bottom:100
            },
            xAxis:{
                type:"category",
                data:names,
                axisLabel:{
                    rotate:40,
                    width:110,
                    overflow:"truncate"
                }
            },
            yAxis:{
                type:"category",
                data:names,
                axisLabel:{
                    width:130,
                    overflow:"truncate"
                }
            },
            visualMap:{
                min:-1,max:1,
                calculable:true,
                orient:"horizontal",
                left:"center",
                bottom:0,
                inRange:{
                    color:["#718096","#F8FAFC","#122B49"]
                }
            },
            series:[{
                type:"heatmap",
                data:cells,
                label:{
                    show:names.length <= 10,
                    formatter:p =>
                        Number(p.value[2]).toFixed(2)
                },
                itemStyle:{
                    borderColor:"#FFFFFF",
                    borderWidth:1
                }
            }]
        },p => openDrawer(
            "Relationship details",
            p.data.relationship
        ),true)
        : empty("No relationships match the filters.");

    const ranked = rows.slice(0,12).map(x => ({
        ...x,
        pair:`${x.column_a} / ${x.column_b}`
    }));

    const categorical = (
        r.categorical_relationships || []
    ).filter(x => matches(x,f.search));

    return panel("Relationship controls",`
        <div class="toolbar">
            ${searchControl(f.search)}
            ${selectControl("method",[
                "pearson","spearman","kendall"
            ],method,"Correlation")}
            ${selectControl("direction",[
                "all","positive","negative"
            ],f.direction || "all","Direction")}
            <label class="muted">
                Minimum |r|:
                <strong>${threshold.toFixed(2)}</strong>
                <input type="range" min="0" max="1"
                    step="0.05" value="${threshold}"
                    data-filter="threshold">
            </label>
        </div>
    `) + panel("Interactive correlation matrix",
        heatmap +
        notice("Blank cells represent unavailable or filtered "
            + "relationships. Correlation is not causation.")
    ) + panel("Ranked relationships",
        bars("ranked-relationships",ranked,
            "pair","coefficient",
            row => openDrawer("Relationship",row))
    ) + panel("Numerical associations",
        table("relationship-table",rows,[
            "column_a","column_b","method",
            "coefficient","adjusted_p_value","observations"
        ])
    ) + panel("Categorical associations",
        bars("categorical-chart",
            categorical.slice(0,12).map(x => ({
                ...x,
                pair:`${x.column_a} / ${x.column_b}`
            })),
            "pair","cramers_v"
        ) +
        table("categorical-table",categorical,[
            "column_a","column_b","cramers_v",
            "adjusted_p_value","assumptions_met"
        ]) +
        notice("Interpret significance tests only when "
            + "their statistical assumptions are appropriate.")
    );
}

function temporal() {

    const r = moduleResult("temporal");
    const f = filters();

    const columns = (r.columns || [])
        .filter(c => c.coverage);

    if (!columns.length)
        return empty("No applicable temporal columns.");

    const c = columns.find(
        x => x.column_name === f.variable
    ) || columns[0];

    const coverage = c.coverage;

    const months = Object.entries(
        c.volume?.monthly_records || {}
    ).sort(([a],[b]) => a.localeCompare(b));

    return panel("Temporal variable",
        selectControl("variable",
            columns.map(x => ({
                value:x.column_name,
                label:x.column_name
            })),c.column_name,"Date column")
    ) + grid(
        kpi("Valid dates",c.valid_dates,"calendar-check") +
        kpi("Observed days",coverage.observed_days,"calendar") +
        kpi("Unobserved days",coverage.unobserved_days,
            "calendar-x") +
        kpi("Calendar coverage",pct(coverage.day_coverage_pct),
            "clock")
    ) + panel("Monthly record volume",
        chart("temporal-chart",{
            tooltip:{trigger:"axis"},
            grid:{
                left:55,right:25,top:45,bottom:75
            },
            xAxis:{
                type:"category",
                data:months.map(x => x[0])
            },
            yAxis:{type:"value"},
            dataZoom:[
                {type:"inside"},
                {type:"slider",bottom:10}
            ],
            series:[{
                type:"line",
                data:months.map(x => x[1]),
                lineStyle:{width:3},
                symbolSize:6,
                areaStyle:{opacity:.12}
            }]
        }) +
        notice("Drag the lower slider to explore available "
            + "monthly periods. Unobserved calendar days "
            + "are not necessarily missing business records.")
    ) + panel("Temporal diagnostics",raw(c));
}

function multicollinearity() {

    const r = moduleResult("multicollinearity");
    const f = filters();

    if (r.status !== "profiled")
        return panel("Analysis availability",
            status(r.status) + raw(r));

    const rows = (r.columns || []).filter(c =>
        matches(c,f.search)
        && (!f.severity || f.severity === "all"
            || c.severity === f.severity)
    );

    const s = r.summary || {};

    return grid(
        kpi("Predictors",s.predictor_count,"network") +
        kpi("Matrix rank",s.matrix_rank,"grid-3x3") +
        kpi("Complete cases",s.complete_case_rows,"database") +
        kpi("Excluded rows",s.excluded_rows,"filter-x")
    ) + panel("Predictor redundancy",`
        <div class="toolbar">
            ${searchControl(f.search)}
            ${selectControl("severity",[
                "all","low","warning",
                "critical","perfect_collinearity"
            ],f.severity || "all","Severity")}
        </div>
    ` + bars("vif-chart",rows,
        "column_name","vif",
        row => columnDetails(row.column_name))
    ) + panel("Variance inflation factors",
        table("vif-table",rows.map(c => ({
            ...c,
            vif:c.vif === null
                && c.severity === "perfect_collinearity"
                ? "Infinite" : c.vif
        })),[
            "column_name","vif","r_squared","severity"
        ]) +
        notice("Infinite VIF is shown in the table, not "
            + "substituted with an arbitrary finite chart value. "
            + "High VIF alone does not justify feature deletion.")
    );
}

function benchmark() {

    const b = DATA.benchmark;
    const f = filters();

    if (!b)
        return empty("Benchmark report not available.");

    const metric = f.metric || "profiling_seconds";

    const rows = (b.datasets || []).map(d => ({
        ...d,
        peak_memory:d.process_memory?.peak_sampled_rss_mb
    }));

    const s = b.summary;

    const engines = Object.entries(
        rows.find(d => d.industry === state.industry)
            ?.module_performance || {}
    ).map(([name,m]) => ({
        module:label(name),
        status:m.status,
        seconds:m.execution_seconds
    }));

    return grid(
        kpi("Datasets passed",s.datasets_passed,"check-circle") +
        kpi("Records processed",s.total_records_processed,
            "database") +
        kpi("Completed executions",
            s.total_module_executions_completed,"cpu") +
        kpi("Total seconds",s.total_seconds,"timer")
    ) + panel("Cross-industry comparison",
        selectControl("metric",[
            "rows","ingestion_seconds",
            "profiling_seconds",
            "profiling_rows_per_second",
            "peak_memory","report_size_kb"
        ],metric,"Performance metric") +
        bars("benchmark-chart",rows,"industry",metric)
    ) + panel("Measured benchmark results",
        table("benchmark-table",rows,[
            "industry","status","rows",
            "ingestion_seconds","profiling_seconds",
            "peak_memory","report_size_kb"
        ])
    ) + panel("Selected industry module performance",
        bars("benchmark-engines",engines,
            "module","seconds")
    ) + panel("Benchmark methodology",
        raw(b.methodology) +
        notice("Single-run measurements, uncontrolled cache "
            + "conditions and sampled process memory limit "
            + "performance generalization.")
    );
}

function information() {

    const r = report();

    return panel("Report metadata",raw({
        report_schema_version:r.report_schema_version,
        generated_at:r.generated_at,
        industry:r.industry,
        source:r.source,
        status:r.status,
        execution:r.execution
    })) + panel("Interpretation boundaries",
        notice("DecisionIQ currently profiles datasets. "
            + "It does not yet validate all business rules, "
            + "predict outcomes or recommend optimal decisions.")
    );
}

const renderers = {
    overview, explorer, structural, statistical,
    missing_values:missing, outliers, relationships,
    temporal, multicollinearity, benchmark, information
};

function render() {

    renderVersion++;

    charts.forEach(c => c.dispose());
    charts = [];
    currentExport = [];

    const page = pages[state.page];
    const r = report();

    $("page-title").textContent = page.title;

    $("breadcrumb").textContent =
        `${page.group} / ${page.title}`;

    $("page-subtitle").textContent =
        `${label(state.industry)} · `
        + `${r.source?.file_name || "Dataset"}`;

    document.querySelectorAll(".nav-item").forEach(el => {
        el.classList.toggle(
            "active",el.dataset.page === state.page
        );
    });

    const moduleName = state.page === "explorer"
        ? "structural" : state.page;

    const module = r.modules?.[moduleName];

    try {

        if (module && module.status !== "completed") {

            $("content").innerHTML = panel(
                "Module unavailable",
                status(module.status) + raw(module)
            );

        } else {

            $("content").innerHTML =
                renderers[state.page]();
        }

    } catch(error) {

        console.error(error);

        $("content").innerHTML = notice(
            "This section could not be rendered. "
            + "Inspect the report schema and browser console."
        );
    }

    document.querySelectorAll("[data-go]")
        .forEach(el => {
            el.onclick = () => go(el.dataset.go);
        });

    document.querySelectorAll("[data-filter]")
        .forEach(el => {
            el.onchange = () =>
                setFilter(el.dataset.filter,el.value);
        });

    icons();
}

function init() {

    if (!window.echarts) {

        $("content").innerHTML = notice(
            "ECharts is missing. Rebuild the dashboard "
            + "with the local visualization assets."
        );

        return;
    }

    $("navigation").innerHTML = NAV.map(
        ([group,items]) => `
            <div class="nav-heading">${esc(group)}</div>
            ${items.map(([key,title,icon]) => `
                <button class="nav-item"
                        data-page="${esc(key)}"
                        title="${esc(title)}">
                    <i data-lucide="${esc(icon)}"></i>
                    <span>${esc(title)}</span>
                </button>
            `).join("")}
        `
    ).join("");

    document.querySelectorAll(".nav-item")
        .forEach(el => {
            el.onclick = () => go(el.dataset.page);
        });

    $("industry").innerHTML = Object.keys(DATA.reports)
        .map(key => `
            <option value="${esc(key)}">
                ${esc(label(key))}
            </option>
        `).join("");

    $("industry").value = state.industry;

    $("industry").onchange = e => {

        state.industry = e.target.value;
        state.tables = {};
        closeDrawer();
        render();
    };

    $("global-search").onkeydown = e => {

        if (e.key === "Enter") {

            state.page = "explorer";
            filters().search = e.target.value;
            state.tables = {};
            render();
        }
    };

    $("toggle-sidebar").onclick = () => {

        document.body.classList.toggle("collapsed");

        setTimeout(() =>
            charts.forEach(c => c.resize()),250);
    };

    $("export-json").onclick = () => {

        const value = state.page === "benchmark"
            ? DATA.benchmark
            : report().modules?.[state.page]?.result
                ?? report();

        download(
            JSON.stringify(value,null,2),
            `decisioniq_${state.industry}_${state.page}.json`,
            "application/json"
        );
    };

    $("print-report").onclick = () => window.print();

    $("close-drawer").onclick = closeDrawer;
    $("overlay").onclick = closeDrawer;

    document.addEventListener("keydown",e => {
        if (e.key === "Escape")
            closeDrawer();
    });

    window.addEventListener("resize",() =>
        charts.forEach(c => c.resize()));

    render();
}

init();
