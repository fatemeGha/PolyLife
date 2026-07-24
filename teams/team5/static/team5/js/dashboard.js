window.onload=loadDashboard;

async function loadDashboard(){
    const user=await api("/whoami/");
    if(user==null){ document.getElementById("login-alert").style.display="block"; return; }
    document.getElementById("navbar-user").innerHTML=user.username;
    document.getElementById("user-name").innerHTML=user.username;
    const [exercises, workouts, favorites, history]=await Promise.all([api("/exercises/"), api("/workouts/"), api("/favorites/"), api("/history/")]);
    document.getElementById("exercise-count").innerHTML=exercises.length;
    document.getElementById("program-count").innerHTML=workouts.length;
    document.getElementById("favorite-count").innerHTML=favorites.length;
    document.getElementById("history-count").innerHTML=history.length;
}