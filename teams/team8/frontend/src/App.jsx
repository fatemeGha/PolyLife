import { ArrowLeft, LogIn, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "./api";
import Activity from "./components/Activity";
import Cart from "./components/Cart";
import ContentHub from "./components/ContentHub";
import Courses from "./components/Courses";
import Discover from "./components/Discover";
import Feed from "./components/Feed";
import MemberProfile from "./components/MemberProfile";
import Messages from "./components/Messages";
import Profile from "./components/Profile";
import Shell from "./components/Shell";
import Studio from "./components/Studio";
import Transactions from "./components/Transactions";
import { ErrorNotice, Loading, Toast } from "./components/UI";

const validPages = new Set([
  "feed",
  "discover",
  "member",
  "messages",
  "hub",
  "courses",
  "cart",
  "transactions",
  "activity",
  "profile",
  "studio",
]);

function routeFromHash() {
  const value = window.location.hash.replace(/^#\/?/, "");
  const [page, kind, id] = value.split("/");
  const active = validPages.has(page) ? page : "feed";
  let context = null;
  if (active === "feed" && kind === "post" && id) context = { postId: id };
  if (active === "member" && kind === "profile" && id) {
    context = { profileId: Number(id) };
  }
  if (active === "messages" && kind === "with" && id) {
    context = { userId: Number(id) };
  }
  if (active === "courses" && kind === "course" && id) context = { courseId: id };
  return { page: active, context };
}

function hashFor(page, context) {
  if (page === "feed" && context?.postId) return `feed/post/${context.postId}`;
  if (page === "member" && context?.profileId) {
    return `member/profile/${context.profileId}`;
  }
  if (page === "messages" && context?.userId) return `messages/with/${context.userId}`;
  if (page === "courses" && context?.courseId) {
    return `courses/course/${context.courseId}`;
  }
  return page;
}

function LoginRequired() {
  return (
    <main className="auth-screen" dir="rtl">
      <div className="auth-screen__brand">
        <span className="brand__mark">P</span>
        <strong>PolyLife</strong>
      </div>
      <section className="auth-card">
        <span className="auth-card__icon">
          <ShieldCheck size={29} />
        </span>
        <span className="eyebrow">ورود امن از طریق Core</span>
        <h1>برای ورود به جامعه آماده‌ای؟</h1>
        <p>
          احراز هویت در سرویس مرکزی PolyLife انجام می‌شود و رمز یا توکن شما وارد
          این میکروسرویس نخواهد شد.
        </p>
        <a className="button button--primary button--wide" href="http://localhost:8000/login">
          <LogIn size={19} />
          ورود به حساب PolyLife
          <ArrowLeft size={18} />
        </a>
      </section>
      <small>Team 8 · Social Network + LMS</small>
    </main>
  );
}

export default function App() {
  const [session, setSession] = useState(null);
  const [active, setActive] = useState(() => routeFromHash().page);
  const [routeContext, setRouteContext] = useState(() => routeFromHash().context);
  const [loading, setLoading] = useState(true);
  const [authRequired, setAuthRequired] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);

  const loadSession = () => {
    setLoading(true);
    setError("");
    api
      .whoami()
      .then((payload) => {
        setSession(payload);
        setAuthRequired(false);
      })
      .catch((reason) => {
        if (reason.status === 401) setAuthRequired(true);
        else setError(reason.message);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadSession();
    const onHashChange = () => {
      const route = routeFromHash();
      setActive(route.page);
      setRouteContext(route.context);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (page, context = null) => {
    window.location.hash = hashFor(page, context);
    setActive(page);
    setRouteContext(context);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const notify = (message, type = "success") => {
    setToast({ message, type });
    window.setTimeout(() => setToast(null), 4200);
  };

  if (loading) {
    return (
      <main className="boot-screen">
        <span className="brand__mark">P</span>
        <Loading label="PolyLife در حال آماده‌شدن است…" />
      </main>
    );
  }
  if (authRequired) return <LoginRequired />;
  if (error) {
    return (
      <main className="boot-screen">
        <ErrorNotice message={error} retry={loadSession} />
      </main>
    );
  }

  const profile = session?.profile;
  const openProfile = (userId) => {
    if (Number(userId) === Number(session.user_id)) navigate("profile");
    else navigate("member", { profileId: Number(userId) });
  };
  const pages = {
    feed: (
      <Feed
        profile={profile}
        notify={notify}
        focusPostId={routeContext?.postId}
        onOpenProfile={openProfile}
        onNavigate={navigate}
      />
    ),
    discover: (
      <Discover
        currentUserId={session.user_id}
        notify={notify}
        onOpenProfile={openProfile}
        onMessage={(userId) => navigate("messages", { userId })}
      />
    ),
    member: (
      <MemberProfile
        userId={routeContext?.profileId}
        currentUserId={session.user_id}
        notify={notify}
        onBack={() => navigate("discover")}
        onMessage={(userId) => navigate("messages", { userId })}
        onOpenProfile={openProfile}
      />
    ),
    messages: <Messages initialUserId={routeContext?.userId} notify={notify} />,
    hub: <ContentHub notify={notify} />,
    courses: (
      <Courses
        notify={notify}
        onNavigate={navigate}
        initialCourseId={routeContext?.courseId}
      />
    ),
    cart: <Cart notify={notify} onNavigate={navigate} />,
    transactions: <Transactions onNavigate={navigate} />,
    activity: <Activity onNavigate={navigate} />,
    profile: (
      <Profile
        profile={profile}
        notify={notify}
        onNavigate={navigate}
        onUpdated={(updated) =>
          setSession((value) => ({ ...value, profile: updated }))
        }
      />
    ),
    studio: <Studio notify={notify} onNavigate={navigate} />,
  };

  return (
    <>
      <Shell
        active={active}
        onNavigate={navigate}
        profile={profile}
        notify={notify}
      >
        {pages[active] || pages.feed}
      </Shell>
      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </>
  );
}
