window.addEventListener("DOMContentLoaded", loadWorkout);

async function loadWorkout() {
    try {
        const data = await api("/workouts/" + programId + "/");
        const workout = Array.isArray(data) ? data[0] : data;
        if (!workout) { document.getElementById("program").innerHTML = `<div class="alert alert-danger">برنامه پیدا نشد.</div>`; return; }
        let hasStarted = false;
        try { const history = await api("/history/"); hasStarted = history.some(item => Number(item.workout.id) === Number(workout.id)); } catch (e) {}
        let exercises = "";
        if (workout.exercises && workout.exercises.length) { workout.exercises.forEach(item => { const ex = item.exercise || {}; exercises += `<tr><td>${ex.title || "-"}</td><td>${item.sets || "-"}</td><td>${item.repeat || "-"}</td></tr>`; }); }
        else { exercises = `<tr><td colspan="3">تمرینی برای این برنامه ثبت نشده است.</td></tr>`; }
        let buttonHTML = hasStarted ? `<div class="alert alert-info mt-4">شما قبلاً این برنامه را شروع کرده‌اید.</div>` : `<div class="mt-4" id="start-button-container"><button id="start-workout-btn" class="btn btn-success btn-lg" onclick="startWorkout(${workout.id}, ${workout.duration || 0})">▶ شروع برنامه تمرینی</button></div>`;
        document.getElementById("program").innerHTML = `<div class="card shadow"><div class="card-body"><h2>${workout.title}</h2><p>${workout.description || ""}</p><hr><p><b>سطح:</b> ${workout.difficulty}</p>${workout.duration ? `<p><b>مدت برنامه:</b> ${workout.duration} دقیقه</p>` : ''}<hr><h4>تمرین‌های برنامه</h4><table class="table table-bordered table-striped"><thead><tr><th>تمرین</th><th>ست</th><th>تکرار</th></tr></thead><tbody>${exercises}</tbody></table>${buttonHTML}</div></div>`;
    } catch (error) {
        document.getElementById("program").innerHTML = `<div class="alert alert-danger">خطا در دریافت اطلاعات برنامه</div>`;
    }
}

async function startWorkout(workoutId, duration) {
    const buttonContainer = document.getElementById("start-button-container");
    const button = document.getElementById("start-workout-btn");
    if (button) { button.disabled = true; button.innerHTML = 'در حال شروع...'; }
    try {
        const result = await api("/history/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workout_id: workoutId, duration: duration || 0, completed: false }) });
        if (result) { if (buttonContainer) buttonContainer.innerHTML = `<div class="alert alert-success">✅ برنامه تمرینی با موفقیت شروع شد.</div>`; setTimeout(() => window.location.href = "/history/", 1400); }
    } catch (error) { if (button) { button.disabled = false; button.innerHTML = '▶ شروع برنامه تمرینی'; } alert("خطا در شروع برنامه"); }
}