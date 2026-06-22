export default function StatsBar() {
  const stats = [
    { title: "مربی متخصص", value: "+۵۰", icon: "👤" },
    { title: "برنامه تمرینی هوشمند", value: "+۱۰۰", icon: "🔗" },
    { title: "کالری سوزانده شده", value: "+۱۰,۰۰۰", icon: "🔥" },
    { title: "پشتیبانی اختصاصی", value: "۲۴/۷", icon: "🎧" },
  ];

  return (
    <div className="bg-[#185E64]/80 backdrop-blur-sm border-b border-white/10 w-full py-6">
      <div className="max-w-6xl mx-auto flex flex-row-reverse justify-around items-center px-4">
        {stats.map((item, index) => (
          <div key={index} className="flex flex-col items-center text-white border-l border-white/20 last:border-0 px-4">
            <span className="text-2xl mb-1">{item.icon}</span>
            <h3 className="text-xl font-bold">{item.value}</h3>
            <p className="text-xs opacity-80">{item.title}</p>
          </div>
        ))}
      </div>
    </div>
  );
}