window.addEventListener("DOMContentLoaded", () => {
    document.getElementById("recommendedBtn").addEventListener("click", loadRecommended);
    loadPrograms();
});

async function loadPrograms(){ const programs=await api("/workouts/"); showPrograms(programs); }
async function loadRecommended(){ const programs=await api("/workouts/recommended/"); showPrograms(programs); }

function showPrograms(programs){
    const div=document.getElementById("program-list"); div.innerHTML="";
    if(!programs || programs.length===0){ div.innerHTML=`<div class="alert alert-info">برنامه‌ای یافت نشد.</div>`; return; }
    programs.forEach(p=>{ div.innerHTML+=`<div class="col-lg-4 col-md-6 mb-4"><div class="card h-100 shadow"><div class="card-body d-flex flex-column"><h4>${p.title}</h4><p>${p.description}</p><p>سطح: <b>${p.difficulty}</b></p><div class="mt-auto"><a href="/workouts/${p.id}/" class="btn btn-primary">جزئیات</a><button class="btn btn-outline-danger" onclick="addFavorite(${p.id})">❤ افزودن به علاقه‌مندی</button></div></div></div></div>`; });
}

async function addFavorite(workoutId) {
    try {
        await api("/favorites/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workout_id: workoutId }) });
        alert("برنامه با موفقیت به علاقه‌مندی‌ها اضافه شد.");
    } catch (err) {
        alert(err.detail || err.non_field_errors?.[0] || "خطا در ثبت علاقه‌مندی.");
    }
}