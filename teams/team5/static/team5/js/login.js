window.onload=function(){ document.getElementById("loginBtn").onclick=login; };

async function login(){
    const username=document.getElementById("username").value;
    const password=document.getElementById("password").value;
    const response=await fetch("/login/api/", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ username, password }) });
    const data=await response.json();
    if(!response.ok){ document.getElementById("msg").innerHTML=data.message; return; }
    localStorage.setItem("token", data.token);
    localStorage.setItem("refresh", data.refresh);
    window.location="/";
}