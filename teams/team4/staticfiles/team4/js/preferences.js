window.onload=init;

async function init(){

    const pref=await api("/preferences/");

    if(pref.length){

        document.getElementById("goal").value=pref[0].goal;

        document.getElementById("level").value=pref[0].level;

        document.getElementById("equipment").value=pref[0].equipment;

    }

    document

    .getElementById("saveBtn")

    .onclick=save;

}

async function save(){

    await api("/preferences/",{

        method:"POST",

        headers:{

            "Content-Type":"application/json"

        },

        body:JSON.stringify({

            goal:goal.value,

            level:level.value,

            equipment:equipment.value

        })

    });

    alert("ذخیره شد");

}