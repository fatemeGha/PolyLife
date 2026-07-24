window.onload = loadExercise;

async function loadExercise() {
    try {
        if (typeof exerciseId === "undefined" || !exerciseId) {
            document.getElementById("exercise-container").innerHTML = `<div class="alert alert-warning">شناسه تمرین تعریف نشده است.</div>`;
            return;
        }
        const ex = await api(`/exercises/${exerciseId}/`);
        if (!ex) { document.getElementById("exercise-container").innerHTML = `<div class="alert alert-info">تمرین پیدا نشد.</div>`; return; }
        document.getElementById("exercise-container").innerHTML = `<div class="card shadow"><div class="card-body"><div class="row"><div class="col-md-5">${ex.image ? `<img src="${ex.image}" class="img-fluid rounded" alt="${ex.title}">` : `<img src="/static/team5/images/no-image.png" class="img-fluid rounded" alt="بدون تصویر">`}</div><div class="col-md-7"><h2>${ex.title}</h2><hr><p><b>عضله هدف:</b> ${ex.target_muscle || '—'}</p><p><b>سطح:</b> ${ex.difficulty || '—'}</p><p><b>تجهیزات:</b> ${ex.equipment || '—'}</p>${ex.duration ? `<p><b>مدت تمرین:</b> ${ex.duration} دقیقه</p>` : ''}${ex.calories ? `<p><b>کالری:</b> ${ex.calories}</p>` : ''}<hr><h5>توضیحات</h5><p>${ex.description || 'توضیحاتی ثبت نشده است.'}</p>${ex.video ? `<hr><h5>ویدئوی آموزشی</h5><div class="ratio ratio-16x9"><iframe src="${ex.video}" allowfullscreen></iframe></div>` : ''}</div></div></div></div>`;
    } catch (error) {
        const container = document.getElementById("exercise-container");
        if (container) container.innerHTML = `<div class="alert alert-danger">خطا در بارگذاری تمرین:<br><small>${error.message}</small></div>`;
    }
}