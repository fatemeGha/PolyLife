(() => {
    "use strict";

    const body = document.body;
    const API_BASE = (body.dataset.apiBase || "/api/team2").replace(/\/$/, "");
    const AUTH_HEADERS = {
        "X-User-Id": body.dataset.userId || "1",
        "X-User-Username": body.dataset.username || "demo-user",
    };
    const STORAGE_DATE_MAP = "polylife-reminder-dates";
    const STORAGE_NOTIFIED = "polylife-notified-reminders";
    const REMINDER_COLORS = ["#e69a51", "#4faebb", "#8cbf77", "#ba84b8", "#d36f64"];

    const state = {
        calendarCursor: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
        selectedDate: new Date(),
        reminders: [],
        records: [],
        summary: null,
        chart: null,
        pendingReminder: null,
        confirmAction: null,
        reminderDates: readStorage(STORAGE_DATE_MAP, {}),
    };

    const $ = (selector, scope = document) => scope.querySelector(selector);
    const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
    const el = {
        welcome: $("#welcomeScreen"), app: $("#appShell"), calendar: $("#calendarGrid"), month: $("#calendarMonth"),
        reminderList: $("#reminderList"), reminderEmpty: $("#reminderEmpty"), reminderCount: $("#reminderCount"),
        recordsBody: $("#recordsBody"), recordsEmpty: $("#recordsEmpty"),
        reminderModal: $("#reminderModal"), recordModal: $("#recordModal"), confirmModal: $("#confirmModal"), quietModal: $("#quietHoursModal"),
        reminderForm: $("#reminderForm"), recordForm: $("#recordForm"), chart: $("#progressChart"), chartEmpty: $("#chartEmpty"),
    };

    document.addEventListener("DOMContentLoaded", initialize);

    function initialize() {
        bindEvents();
        renderToday();
        renderCalendar();
        if (sessionStorage.getItem("polylife-started") === "1") showApp(false);
        refreshDashboard();
        window.setInterval(checkDueReminders, 30000);
    }

    function bindEvents() {
        $("#getStartedButton").addEventListener("click", () => showApp(true));
        $("#previousMonth").addEventListener("click", () => changeMonth(-1));
        $("#nextMonth").addEventListener("click", () => changeMonth(1));
        $("#addRecordButton").addEventListener("click", openRecordModal);
        $("#emptyAddRecordButton").addEventListener("click", openRecordModal);
        $("#notificationButton").addEventListener("click", requestNotifications);
        $$(".tab-button").forEach(button => button.addEventListener("click", () => activateTab(button.dataset.tab)));
        $$('[data-close-modal]').forEach(button => button.addEventListener("click", () => closeModal(button.dataset.closeModal)));
        $$(".modal-backdrop").forEach(modal => modal.addEventListener("mousedown", event => { if (event.target === modal && modal.id !== "confirmModal") closeModal(modal.id); }));
        document.addEventListener("keydown", event => { if (event.key === "Escape") closeTopModal(); });
        el.reminderForm.addEventListener("submit", submitReminder);
        el.recordForm.addEventListener("submit", submitRecord);
        $("#confirmCancel").addEventListener("click", () => closeModal("confirmModal"));
        $("#confirmAccept").addEventListener("click", executeConfirmation);
        $("#quietHoursCancel").addEventListener("click", () => closeModal("quietHoursModal"));
        $("#quietHoursAccept").addEventListener("click", submitQuietHoursOverride);
        $("#metricSelect").addEventListener("change", loadChart);
        $("#periodSelect").addEventListener("change", loadChart);
    }

    function showApp(animated) {
        sessionStorage.setItem("polylife-started", "1");
        if (!animated) { el.welcome.classList.add("is-hidden"); el.app.classList.remove("is-hidden"); return; }
        el.welcome.classList.add("is-leaving");
        window.setTimeout(() => { el.welcome.classList.add("is-hidden"); el.app.classList.remove("is-hidden"); }, 480);
    }

    async function refreshDashboard() {
        const [reminders, records, summary] = await Promise.allSettled([
            api("/reminders/?include_completed=false"), api("/progress/records/"), api("/progress/summary/")
        ]);
        if (reminders.status === "fulfilled") state.reminders = reminders.value.data?.reminders || [];
        else showToast("Could not load reminders", readableError(reminders.reason), true);
        if (records.status === "fulfilled") state.records = records.value.data?.records || [];
        else showToast("Could not load records", readableError(records.reason), true);
        if (summary.status === "fulfilled") state.summary = summary.value.data || null;
        renderReminders(); renderCalendar(); renderRecords(); renderSummary();
        await loadChart(); checkDueReminders();
    }

    async function api(path, options = {}) {
        const headers = { Accept: "application/json", ...AUTH_HEADERS, ...(options.headers || {}) };
        if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
        const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
        let payload = null;
        try { payload = await response.json(); } catch { payload = { message: `Server returned ${response.status}.` }; }
        if (!response.ok || payload?.success === false) {
            const error = new Error(payload?.message || `Request failed (${response.status})`);
            error.status = response.status; error.payload = payload; throw error;
        }
        return payload;
    }

    function renderToday() {
        const now = new Date();
        $("#todayWeekday").textContent = now.toLocaleDateString("en-US", { weekday: "long" });
        $("#todayDate").textContent = now.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
        updateNotificationDot();
    }

    function changeMonth(delta) {
        state.calendarCursor = new Date(state.calendarCursor.getFullYear(), state.calendarCursor.getMonth() + delta, 1);
        renderCalendar();
    }

    function renderCalendar() {
        const cursor = state.calendarCursor;
        el.month.textContent = cursor.toLocaleDateString("en-US", { month: "long", year: "numeric" });
        el.calendar.innerHTML = "";
        const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
        const start = new Date(first); start.setDate(first.getDate() - first.getDay());
        for (let i = 0; i < 42; i += 1) {
            const date = new Date(start); date.setDate(start.getDate() + i);
            const key = localDateKey(date); const reminders = remindersForDate(key);
            const button = document.createElement("button");
            button.type = "button"; button.className = "calendar-day"; button.textContent = date.getDate();
            button.setAttribute("role", "gridcell");
            button.setAttribute("aria-label", date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }));
            if (date.getMonth() !== cursor.getMonth()) button.classList.add("is-outside");
            if (sameDay(date, new Date())) button.classList.add("is-today");
            if (sameDay(date, state.selectedDate)) button.classList.add("is-selected");
            if (reminders.length) { button.classList.add("has-reminder"); button.style.setProperty("--reminder-color", colorForReminder(reminders[0], 0)); }
            button.addEventListener("click", () => openReminderModal(date));
            el.calendar.appendChild(button);
        }
    }

    function openReminderModal(date) {
        state.selectedDate = new Date(date);
        renderCalendar();
        $("#selectedReminderDate").textContent = date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
        el.reminderForm.reset();
        const next = new Date(Date.now() + 60 * 60 * 1000);
        $("#reminderHour").value = String(next.getHours()).padStart(2, "0");
        $("#reminderMinute").value = String(Math.ceil(next.getMinutes() / 5) * 5 % 60).padStart(2, "0");
        $("#reminderFormError").textContent = "";
        openModal("reminderModal", "#reminderMessage");
    }

    async function submitReminder(event) {
        event.preventDefault();
        const hour = Number($("#reminderHour").value); const minute = Number($("#reminderMinute").value);
        const message = $("#reminderMessage").value.trim();
        if (!Number.isInteger(hour) || hour < 0 || hour > 23 || !Number.isInteger(minute) || minute < 0 || minute > 59 || !message) {
            $("#reminderFormError").textContent = "Enter a valid time and a short reminder message."; return;
        }
        const payload = { title: message.slice(0, 72), message, reminder_time: `${pad(hour)}:${pad(minute)}`, recurrence_pattern: $("#reminderRecurrence").value };
        await createReminder(payload, false);
    }

    async function createReminder(payload, force) {
        const button = el.reminderForm.querySelector("button[type=submit]"); setLoading(button, true, "Saving…");
        try {
            const result = await api("/reminders/", { method: "POST", body: JSON.stringify({ ...payload, force_send_in_quiet_hours: force }) });
            const reminder = result.data;
            state.reminderDates[String(reminder.id)] = localDateKey(state.selectedDate);
            writeStorage(STORAGE_DATE_MAP, state.reminderDates);
            closeModal("reminderModal"); closeModal("quietHoursModal");
            showToast("Reminder saved", `${payload.reminder_time} · ${payload.title}`);
            await reloadReminders();
            if (!state.reminders.some(item => String(item.id) === String(reminder.id))) {
                state.reminders.unshift(reminder);
                renderReminders(); renderCalendar();
            }
            scheduleBrowserReminder(reminder);
        } catch (error) {
            if (error.status === 409 && error.payload?.errors?.quiet_hours_conflict && !force) {
                state.pendingReminder = payload; closeModal("reminderModal"); openModal("quietHoursModal", "#quietHoursCancel");
            } else $("#reminderFormError").textContent = readableError(error);
        } finally { setLoading(button, false); }
    }

    async function submitQuietHoursOverride() {
        if (!state.pendingReminder) return;
        const payload = state.pendingReminder; state.pendingReminder = null;
        closeModal("quietHoursModal");
        await createReminder(payload, true);
    }

    async function reloadReminders() {
        try { const result = await api("/reminders/?include_completed=false"); state.reminders = result.data?.reminders || []; renderReminders(); renderCalendar(); }
        catch (error) { showToast("Refresh failed", readableError(error), true); }
    }

    function renderReminders() {
        const reminders = [...state.reminders].sort((a, b) => reminderSortKey(a).localeCompare(reminderSortKey(b)));
        el.reminderList.innerHTML = ""; el.reminderCount.textContent = reminders.length;
        el.reminderEmpty.classList.toggle("is-hidden", reminders.length !== 0);
        el.reminderList.classList.toggle("is-hidden", reminders.length === 0);
        reminders.forEach((reminder, index) => {
            const item = document.createElement("button"); item.type = "button"; item.className = "reminder-item";
            const key = reminderDateKey(reminder); const date = parseLocalDate(key);
            const color = colorForReminder(reminder, index); item.style.setProperty("--item-color", color);
            item.innerHTML = `<span class="reminder-color"></span><span class="reminder-copy"><strong></strong><span></span></span><span class="reminder-time"><strong></strong><span></span></span>`;
            $(".reminder-copy strong", item).textContent = reminder.message || reminder.title || "Reminder";
            $(".reminder-copy span", item).textContent = date.toLocaleDateString("en-US", { month: "short", day: "numeric", weekday: "short" });
            $(".reminder-time strong", item).textContent = normalizeTime(reminder.reminder_time);
            $(".reminder-time span", item).textContent = reminder.recurrence_pattern === "none" ? "once" : reminder.recurrence_pattern;
            item.addEventListener("click", () => confirmRemoval("reminder", reminder));
            el.reminderList.appendChild(item);
        });
    }

    function confirmRemoval(type, item) {
        state.confirmAction = { type, item };
        $("#confirmTitle").textContent = type === "reminder" ? "Remove this reminder?" : "Remove this record?";
        $("#confirmMessage").textContent = type === "reminder" ? (item.message || item.title || "This reminder") : `The measurement from ${formatRecordDate(item.created_at)} will be removed.`;
        openModal("confirmModal", "#confirmCancel");
    }

    async function executeConfirmation() {
        const action = state.confirmAction; if (!action) return;
        const button = $("#confirmAccept"); setLoading(button, true, "Removing…");
        try {
            const path = action.type === "reminder" ? `/reminders/${encodeURIComponent(action.item.id)}/` : `/progress/records/${encodeURIComponent(action.item.id)}/`;
            await api(path, { method: "DELETE" });
            if (action.type === "reminder") { delete state.reminderDates[String(action.item.id)]; writeStorage(STORAGE_DATE_MAP, state.reminderDates); await reloadReminders(); }
            else await reloadProgress();
            closeModal("confirmModal"); showToast("Removed", action.type === "reminder" ? "The reminder was removed." : "The record was removed.");
        } catch (error) { showToast("Could not remove item", readableError(error), true); }
        finally { setLoading(button, false); state.confirmAction = null; }
    }

    function openRecordModal() {
        el.recordForm.reset(); $("#recordFormError").textContent = "";
        const latest = state.records[0] || state.summary?.current;
        if (latest?.height) $("#recordHeight").value = latest.height;
        openModal("recordModal", "#recordWeight");
    }

    async function submitRecord(event) {
        event.preventDefault();
        const payload = {
            weight: numberValue("#recordWeight"), height: numberValue("#recordHeight"),
            body_fat_percentage: optionalNumberValue("#recordBodyFat"), muscle_mass: optionalNumberValue("#recordMuscle"),
            notes: $("#recordNotes").value.trim(),
        };
        if (!payload.weight || !payload.height) { $("#recordFormError").textContent = "Weight and height are required."; return; }
        Object.keys(payload).forEach(key => payload[key] === null && delete payload[key]);
        const button = el.recordForm.querySelector("button[type=submit]"); setLoading(button, true, "Adding…");
        try {
            await api("/progress/records/", { method: "POST", body: JSON.stringify(payload) });
            closeModal("recordModal"); showToast("Record added", "Analytics have been updated with your new measurement."); await reloadProgress();
        } catch (error) { $("#recordFormError").textContent = readableError(error); }
        finally { setLoading(button, false); }
    }

    async function reloadProgress() {
        const [records, summary] = await Promise.all([api("/progress/records/"), api("/progress/summary/")]);
        state.records = records.data?.records || []; state.summary = summary.data || null;
        renderRecords(); renderSummary(); await loadChart();
    }

    function renderRecords() {
        el.recordsBody.innerHTML = "";
        el.recordsEmpty.classList.toggle("is-hidden", state.records.length !== 0);
        $(".table-wrap").classList.toggle("is-hidden", state.records.length === 0);
        state.records.forEach(record => {
            const row = document.createElement("tr");
            row.innerHTML = `<td></td><td></td><td></td><td></td><td></td><td></td><td><button class="row-action" type="button" aria-label="Remove record">×</button></td>`;
            const cells = $$('td', row);
            cells[0].textContent = formatRecordDate(record.created_at);
            cells[1].innerHTML = metricHtml(record.weight, "kg"); cells[2].innerHTML = metricHtml(record.height, "cm");
            cells[3].innerHTML = metricHtml(record.bmi, ""); cells[4].innerHTML = metricHtml(record.body_fat_percentage, "%"); cells[5].innerHTML = metricHtml(record.muscle_mass, "kg");
            $("button", row).addEventListener("click", () => confirmRemoval("record", record));
            el.recordsBody.appendChild(row);
        });
    }

    function renderSummary() {
        const current = state.summary?.current || state.records[0] || {};
        setText("#currentWeight", displayNumber(current.weight)); setText("#currentBmi", displayNumber(current.bmi));
        setText("#currentBodyFat", displayNumber(current.body_fat_percentage)); setText("#currentMuscle", displayNumber(current.muscle_mass));
        setText("#bmiCategory", current.bmi_category || "No data yet"); setText("#analyticsBmi", displayNumber(current.bmi));
        setText("#analyticsBmiCategory", current.bmi_category || "No measurement");
        const bmi = Number(current.bmi); const position = Number.isFinite(bmi) ? Math.max(3, Math.min(97, ((bmi - 13) / 27) * 100)) : 50;
        $(".bmi-scale i").style.setProperty("--bmi-position", `${position}%`);
        if (state.records.length > 1) {
            const newest = Number(state.records[0].weight), oldest = Number(state.records[state.records.length - 1].weight), delta = newest - oldest;
            setText("#weightChange", `${delta > 0 ? "+" : ""}${delta.toFixed(1)} kg across ${state.records.length} records`);
        } else setText("#weightChange", state.records.length ? "Your first measurement" : "Add a record to begin");
        renderInsight();
    }

    function activateTab(name) {
        $$(".tab-button").forEach(button => button.classList.toggle("is-active", button.dataset.tab === name));
        $$(".tab-panel").forEach(panel => panel.classList.toggle("is-hidden", panel.dataset.panel !== name));
        if (name === "analytics") loadChart();
    }

    async function loadChart() {
        const metric = $("#metricSelect").value; const period = $("#periodSelect").value;
        try { const result = await api(`/progress/charts/?metric=${encodeURIComponent(metric)}&period=${encodeURIComponent(period)}`); state.chart = result.data; }
        catch { state.chart = chartFallback(metric, period); }
        renderChart();
    }

    function renderChart() {
        const data = state.chart || {}; const points = (data.points || []).filter(point => Number.isFinite(Number(point.value)));
        const label = metricLabel(data.metric || $("#metricSelect").value); setText("#chartMetricLabel", label);
        setText("#chartLatest", points.length ? `${displayNumber(points[points.length - 1].value)} ${data.unit || metricUnit(data.metric)}`.trim() : "—");
        el.chartEmpty.classList.toggle("is-hidden", points.length !== 0); el.chart.innerHTML = "";
        if (!points.length) { setText("#chartTrend", "No trend yet"); return; }
        const width = 800, height = 360, padX = 66, padY = 38, graphW = width - padX * 2, graphH = height - padY * 2;
        const values = points.map(p => Number(p.value)); let min = Math.min(...values), max = Math.max(...values);
        const spread = max - min || Math.max(Math.abs(max) * .08, 1); min -= spread * .18; max += spread * .18;
        const svg = el.chart; svg.innerHTML = `<defs><linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#185e64" stop-opacity=".23"/><stop offset="100%" stop-color="#185e64" stop-opacity="0"/></linearGradient></defs>`;
        for (let i = 0; i < 5; i += 1) {
            const y = padY + graphH * i / 4; const value = max - (max - min) * i / 4;
            appendSvg(svg, "line", { x1: padX, y1: y, x2: width - padX, y2: y, class: "chart-grid-line" });
            const text = appendSvg(svg, "text", { x: padX - 14, y: y + 4, class: "chart-axis-label", "text-anchor": "end" }); text.textContent = trimNumber(value);
        }
        const coords = points.map((point, index) => ({
            x: padX + (points.length === 1 ? graphW / 2 : graphW * index / (points.length - 1)),
            y: padY + graphH - ((Number(point.value) - min) / (max - min)) * graphH,
            point,
        }));
        const linePath = coords.map((p, i) => `${i ? "L" : "M"}${p.x},${p.y}`).join(" ");
        const areaPath = `${linePath} L${coords[coords.length - 1].x},${height - padY} L${coords[0].x},${height - padY} Z`;
        appendSvg(svg, "path", { d: areaPath, class: "chart-area-fill" }); appendSvg(svg, "path", { d: linePath, class: "chart-line" });
        coords.forEach((p, index) => {
            const circle = appendSvg(svg, "circle", { cx: p.x, cy: p.y, r: 5, class: "chart-point" });
            const title = appendSvg(circle, "title", {}); title.textContent = `${p.point.date}: ${p.point.value} ${data.unit || ""}`;
            if (points.length <= 8 || index === 0 || index === points.length - 1) {
                const text = appendSvg(svg, "text", { x: p.x, y: height - 12, class: "chart-axis-label", "text-anchor": "middle" }); text.textContent = shortDate(p.point.date);
            }
        });
        const delta = values[values.length - 1] - values[0]; setText("#chartTrend", points.length < 2 ? "First data point" : `${delta > 0 ? "↑" : delta < 0 ? "↓" : "→"} ${Math.abs(delta).toFixed(1)} ${data.unit || ""}`);
    }

    function renderInsight() {
        if (state.records.length < 2) { setText("#analyticsInsight", "Add at least two records to receive a progress insight."); return; }
        const newest = state.records[0], oldest = state.records[state.records.length - 1]; const delta = Number(newest.weight) - Number(oldest.weight);
        const direction = delta < 0 ? "decreased" : delta > 0 ? "increased" : "held steady";
        let insight = `Your weight has ${direction}${delta ? ` by ${Math.abs(delta).toFixed(1)} kg` : ""} across ${state.records.length} check-ins.`;
        if (state.summary?.goal?.target_weight != null && state.summary?.progress?.weight_remaining != null) insight += ` You are ${state.summary.progress.weight_remaining} kg from your target.`;
        setText("#analyticsInsight", insight);
    }

    async function requestNotifications() {
        if (!("Notification" in window)) { showToast("Notifications unavailable", "This browser does not support system notifications.", true); return; }
        const permission = await Notification.requestPermission(); updateNotificationDot();
        showToast(permission === "granted" ? "Notifications enabled" : "Notifications not enabled", permission === "granted" ? "PolyLife can alert you while this page is open." : "You can change this permission in browser settings.", permission !== "granted");
    }

    function checkDueReminders() {
        const now = new Date(); const notified = readStorage(STORAGE_NOTIFIED, {});
        state.reminders.forEach(reminder => {
            const time = normalizeTime(reminder.reminder_time); const due = `${reminderDateKey(reminder)}T${time}`;
            const dueDate = new Date(due); const key = `${reminder.id}:${due}`;
            if (!Number.isNaN(dueDate.getTime()) && now >= dueDate && now.getTime() - dueDate.getTime() < 90 * 1000 && !notified[key]) {
                deliverNotification(reminder); notified[key] = new Date().toISOString();
            }
        });
        writeStorage(STORAGE_NOTIFIED, notified);
    }

    function scheduleBrowserReminder(reminder) {
        const due = new Date(`${reminderDateKey(reminder)}T${normalizeTime(reminder.reminder_time)}`); const delay = due.getTime() - Date.now();
        if (delay > 0 && delay < 2147483647) window.setTimeout(() => deliverNotification(reminder), delay);
    }

    function deliverNotification(reminder) {
        const message = reminder.message || reminder.title || "It is time for your PolyLife reminder.";
        showToast("Reminder", message);
        if ("Notification" in window && Notification.permission === "granted") new Notification("PolyLife reminder", { body: message, tag: `polylife-${reminder.id}` });
    }

    function updateNotificationDot() { $("#notificationDot").classList.toggle("is-enabled", "Notification" in window && Notification.permission === "granted"); }
    function openModal(id, focusSelector) { const modal = document.getElementById(id); modal.classList.remove("is-hidden"); document.body.style.overflow = "hidden"; window.setTimeout(() => $(focusSelector, modal)?.focus(), 30); }
    function closeModal(id) { document.getElementById(id)?.classList.add("is-hidden"); if (!$(".modal-backdrop:not(.is-hidden)")) document.body.style.overflow = ""; }
    function closeTopModal() { const open = $$(".modal-backdrop:not(.is-hidden)").pop(); if (open && open.id !== "confirmModal") closeModal(open.id); }
    function setLoading(button, active, label) { if (active) { button.dataset.label = button.textContent; button.textContent = label; button.disabled = true; } else { button.textContent = button.dataset.label || button.textContent; button.disabled = false; } }
    function showToast(title, message, isError = false) { const toast = document.createElement("div"); toast.className = `toast${isError ? " is-error" : ""}`; toast.innerHTML = `<span class="toast-icon">${isError ? "!" : "✓"}</span><span class="toast-copy"><strong></strong><span></span></span>`; $("strong", toast).textContent = title; $(".toast-copy > span", toast).textContent = message; $("#toastRegion").appendChild(toast); window.setTimeout(() => toast.remove(), 4300); }
    function readableError(error) { const errors = error?.payload?.errors; if (errors && typeof errors === "object") { const first = Object.values(errors)[0]; if (typeof first === "string") return first; } return error?.message || "Please try again."; }
    function remindersForDate(key) { return state.reminders.filter(reminder => reminderDateKey(reminder) === key); }
    function reminderDateKey(reminder) { return reminder.reminder_date || reminder.date || reminder.scheduled_date || state.reminderDates[String(reminder.id)] || localDateKey(new Date(reminder.created_at || Date.now())); }
    function reminderSortKey(reminder) { return `${reminderDateKey(reminder)}T${normalizeTime(reminder.reminder_time)}`; }
    function colorForReminder(reminder, index) { const source = String(reminder.id || index); let hash = 0; for (const char of source) hash = (hash * 31 + char.charCodeAt(0)) >>> 0; return REMINDER_COLORS[hash % REMINDER_COLORS.length]; }
    function chartFallback(metric, period) { const days = { weekly: 7, monthly: 30, yearly: 365 }[period] || 30; const cutoff = Date.now() - days * 86400000; return { metric, period, unit: metricUnit(metric), points: [...state.records].reverse().filter(r => new Date(r.created_at).getTime() >= cutoff && r[metric] != null).map(r => ({ date: localDateKey(new Date(r.created_at)), value: Number(r[metric]) })) }; }
    function metricLabel(metric) { return ({ weight: "Weight", bmi: "Body mass index", body_fat_percentage: "Body fat", muscle_mass: "Muscle mass" })[metric] || "Progress"; }
    function metricUnit(metric) { return ({ weight: "kg", bmi: "", body_fat_percentage: "%", muscle_mass: "kg" })[metric] || ""; }
    function metricHtml(value, unit) { return value == null ? "—" : `<span class="record-value">${escapeHtml(displayNumber(value))}</span><span class="unit">${escapeHtml(unit)}</span>`; }
    function formatRecordDate(value) { if (!value) return "—"; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); }
    function shortDate(value) { const date = parseLocalDate(value); return date.toLocaleDateString("en-US", { month: "short", day: "numeric" }); }
    function localDateKey(date) { const y = date.getFullYear(), m = pad(date.getMonth() + 1), d = pad(date.getDate()); return `${y}-${m}-${d}`; }
    function parseLocalDate(key) { const parts = String(key).slice(0, 10).split("-").map(Number); return new Date(parts[0], (parts[1] || 1) - 1, parts[2] || 1); }
    function sameDay(a, b) { return localDateKey(a) === localDateKey(b); }
    function normalizeTime(value) { const match = String(value || "00:00").match(/(\d{1,2}):(\d{2})/); return match ? `${pad(Number(match[1]))}:${match[2]}` : "00:00"; }
    function pad(value) { return String(value).padStart(2, "0"); }
    function numberValue(selector) { return Number($(selector).value); }
    function optionalNumberValue(selector) { const value = $(selector).value.trim(); return value === "" ? null : Number(value); }
    function displayNumber(value) { return value == null || value === "" || Number.isNaN(Number(value)) ? "—" : trimNumber(Number(value)); }
    function trimNumber(value) { return Number(value.toFixed(2)).toString(); }
    function setText(selector, value) { $(selector).textContent = value; }
    function readStorage(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch { return fallback; } }
    function writeStorage(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage can be blocked */ } }
    function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]); }
    function appendSvg(parent, tag, attrs) { const node = document.createElementNS("http://www.w3.org/2000/svg", tag); Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value)); parent.appendChild(node); return node; }
})();
