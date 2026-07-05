window.addEventListener("DOMContentLoaded", loadHistory);

async function loadHistory() {

    try {

        const history = await apiGet("/history/");

        const tbody = document.getElementById("historyTable");

        tbody.innerHTML = "";

        if (!history || history.length === 0) {

            tbody.innerHTML = `
<tr>
<td colspan="4" class="text-center text-muted">
هیچ سابقه‌ای وجود ندارد.
</td>
</tr>
`;

            return;
        }

        history.forEach(h => {

            const workoutTitle = h.workout?.title || "-";

            const status = h.completed
                ? "✅ پایان یافته"
                : "🟡 در حال انجام";

            const operation = h.completed
                ? `
<div class="d-flex gap-2">

<span class="text-success">
${new Date(h.completed_at).toLocaleString("fa-IR")}
</span>

<button
class="btn btn-danger btn-sm"
onclick="deleteHistory(${h.id})">

حذف

</button>

</div>
`
                :
`
<div class="d-flex gap-2">

<button
class="btn btn-success btn-sm"
onclick="finishWorkout(${h.id})">

اتمام تمرین

</button>

<button
class="btn btn-danger btn-sm"
onclick="deleteHistory(${h.id})">

حذف

</button>

</div>
`;

            tbody.innerHTML += `

<tr>

<td>

${workoutTitle}

</td>

<td>

${status}

</td>

<td>

${h.duration} دقیقه

</td>

<td>

${operation}

</td>

</tr>

`;

        });

    }
    catch (err) {

        console.error(err);

        document.getElementById("historyTable").innerHTML = `

<tr>

<td colspan="4" class="text-danger text-center">

خطا در دریافت اطلاعات

</td>

</tr>

`;

    }

}


async function finishWorkout(id) {

    try {

        await apiPost("/history/" + id + "/finish/", {});

        alert("تمرین با موفقیت پایان یافت.");

        loadHistory();

    }
    catch (err) {

        alert(err.detail || "خطا در پایان تمرین");

    }

}


async function deleteHistory(id) {

    if (!confirm("آیا از حذف این سابقه مطمئن هستید؟")) {
        return;
    }

    try {

        await apiDelete("/history/" + id + "/");

        alert("سابقه حذف شد.");

        loadHistory();

    }
    catch (err) {

        alert(err.detail || "خطا در حذف سابقه");

    }

}