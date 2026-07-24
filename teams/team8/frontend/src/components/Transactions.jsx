import {
  CheckCircle2,
  GraduationCap,
  ReceiptText,
} from "lucide-react";
import { useEffect, useState } from "react";
import { api, results } from "../api";
import { EmptyState, ErrorNotice, Loading } from "./UI";

const number = new Intl.NumberFormat("fa-IR");
const date = new Intl.DateTimeFormat("fa-IR", {
  year: "numeric",
  month: "long",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export default function Transactions({ onNavigate }) {
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      setPurchases(results(await api.purchases()));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <section>
      <div className="page-heading">
        <div>
          <span className="eyebrow">حساب مالی</span>
          <h1>تراکنش‌ها و سابقه خرید</h1>
          <p>رسید دوره‌های خریداری‌شده و شماره پیگیری هر پرداخت را اینجا ببین.</p>
        </div>
        <span className="heading-icon">
          <ReceiptText size={28} />
        </span>
      </div>

      {error && <ErrorNotice message={error} retry={load} />}
      {loading ? (
        <Loading label="سوابق خرید را دریافت می‌کنیم…" />
      ) : purchases.length ? (
        <div className="transaction-list">
          {purchases.map((purchase) => (
            <article className="card transaction-row" key={purchase.id}>
              <span className="transaction-row__icon">
                <CheckCircle2 size={24} />
              </span>
              <div>
                <span className="eyebrow">پرداخت موفق</span>
                <h2>{purchase.course.title}</h2>
                <p>
                  {date.format(new Date(purchase.paid_at))} · پیگیری{" "}
                  <b dir="ltr">{purchase.reference}</b>
                </p>
              </div>
              <strong>{number.format(purchase.amount)} تومان</strong>
              <button
                type="button"
                className="button button--secondary"
                onClick={() => onNavigate("courses", { courseId: purchase.course.id })}
              >
                <GraduationCap size={18} />
                مشاهده دوره
              </button>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={ReceiptText}
          title="هنوز خریدی ثبت نشده"
          description="پس از پرداخت یک دوره پولی، رسید آن در این صفحه و پروفایل نمایش داده می‌شود."
          action={
            <button
              type="button"
              className="button button--primary"
              onClick={() => onNavigate("courses")}
            >
              کشف دوره‌ها
            </button>
          }
        />
      )}
    </section>
  );
}
