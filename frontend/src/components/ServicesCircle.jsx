export default function ServicesCircle() {
  // لیست کامل میکروسرویس‌های شما (8 تایی)
  const services = [
    { name: 'PolyWorkout', top: '10%', left: '50%' },
    { name: 'PolyDiet', top: '25%', left: '80%' },
    { name: 'PolyShop', top: '55%', left: '85%' },
    { name: 'PolySocial', top: '75%', left: '60%' },
    { name: 'PolyGroupie', top: '75%', left: '30%' },
    { name: 'PolyAnalysis', top: '55%', left: '10%' },
    { name: 'PolyChallenge', top: '25%', left: '15%' },
    { name: 'PolyProgress', top: '10%', left: '40%' },
  ];

  return (
    <section className="py-20 bg-white flex flex-col items-center">
      <h2 className="text-3xl font-bold text-primary mb-16">اکوسیستم هوشمند پلی‌لایف</h2>
      
      {/* دایره مرکزی و میکروسرویس‌ها */}
      <div className="relative w-[500px] h-[500px] rounded-full border-2 border-dashed border-secondary flex items-center justify-center">
        
        {/* هسته مرکزی */}
        <div className="w-40 h-40 bg-primary text-white rounded-full flex items-center justify-center font-bold text-xl shadow-xl z-10">
          PolyLife
        </div>

        {/* چیدمان 8 میکروسرویس دور دایره */}
        {services.map((service, index) => (
          <div 
            key={index} 
            className="absolute bg-light text-primary px-4 py-2 rounded-lg font-semibold shadow-md border border-secondary text-sm hover:scale-110 transition-transform cursor-pointer whitespace-nowrap"
            style={{ top: service.top, left: service.left }}
          >
            {service.name}
          </div>
        ))}
      </div>
    </section>
  );
}