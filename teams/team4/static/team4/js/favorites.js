window.addEventListener("DOMContentLoaded",loadFavorites);


async function loadFavorites(){

    const data=await api("/favorites/");

    const div=document.getElementById("favorite-list");

    div.innerHTML="";

    if(!data || data.length===0){

        div.innerHTML=`

<div class="alert alert-info">

هنوز موردی به علاقه‌مندی‌ها اضافه نشده است.

</div>

`;

        return;

    }

    data.forEach(item=>{

        /*
        Serializer ممکن است یکی از دو حالت زیر باشد

        workout:{
            ...
        }

        یا

        workout_id
        */

        const workout=item.workout || {};

        div.innerHTML+=`

<div class="card mb-3 shadow">

<div class="card-body">

<h4>

${workout.title || "برنامه تمرینی"}

</h4>

<p>

${workout.description || ""}

</p>

<p>

سطح:
${workout.difficulty || "-"}

</p>

<button
class="btn btn-danger"
onclick="deleteFavorite(${item.id})">

حذف

</button>

</div>

</div>

`;

    });

}



async function deleteFavorite(id){

    if(!confirm("حذف شود؟"))
        return;

    const response=await api("/favorites/"+id+"/",{

        method:"DELETE"

    });

    loadFavorites();

}