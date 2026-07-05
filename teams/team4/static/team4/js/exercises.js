window.addEventListener("DOMContentLoaded", () => {

    document
        .getElementById("filterBtn")
        .addEventListener("click", loadExercises);

    loadExercises();

});

async function loadExercises(){

    let url="/exercises/?";

    const search=document.getElementById("search").value.trim();
    const muscle=document.getElementById("muscle").value;
    const difficulty=document.getElementById("difficulty").value;
    const equipment=document.getElementById("equipment").value;

    if(search)
        url+="search="+encodeURIComponent(search)+"&";

    if(muscle)
        url+="muscle="+encodeURIComponent(muscle)+"&";

    if(difficulty)
        url+="difficulty="+difficulty+"&";

    if(equipment)
        url+="equipment="+equipment+"&";

    const data=await api(url);

    const list=document.getElementById("exercise-list");

    list.innerHTML="";

    if(!data || data.length===0){

        list.innerHTML=`
        <div class="alert alert-warning">
            تمرینی پیدا نشد.
        </div>
        `;

        return;

    }

    data.forEach(ex=>{

        list.innerHTML+=`

<div class="col-lg-4 col-md-6 mb-4">

<div class="card h-100 shadow">

<img
src="${ex.image}"
class="card-img-top"
style="height:220px;object-fit:cover">

<div class="card-body d-flex flex-column">

<h5>${ex.title}</h5>

<p class="text-muted">
عضله:
<b>${ex.target_muscle}</b>
</p>

<p>
سطح:
${ex.difficulty}
</p>

<p>
تجهیزات:
${ex.equipment}
</p>

<div class="mt-auto">

<a
class="btn btn-success"
href="/exercises/${ex.id}/">

جزئیات

</a>

</div>

</div>

</div>

</div>

`;

    });

}