// src/components/SimpleStats.jsx
const SimpleStats = () => {
  const stats = [
    { icon: "🎧", value: "24/7", label: "پشتیبانی اختصاصی" },
    { icon: "🔥", value: "+10,000", label: "کالری سوزانده شده" },
    { icon: "📋", value: "+100", label: "برنامه تمرینی هوشمند" },
    { icon: "👤", value: "+50", label: "مربی متخصص" }
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 px-12 py-10 my-10 max-w-6xl mx-auto">
      {stats.map((stat, index) => (
        <div key={index} className="text-center relative group">
          <div className="text-5xl mb-3">{stat.icon}</div>
          <div className="text-3xl md:text-4xl font-bold text-white">{stat.value}</div>
          <div className="text-sm text-white/80 mt-1">{stat.label}</div>
        </div>
      ))}
    </div>
  );
};

export default SimpleStats;