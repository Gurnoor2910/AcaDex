// Firebase configuration
// <i class="fas fa-exclamation-triangle"></i> IMPORTANT: Get your apiKey and appId from the Firebase Console 
// (Project Settings -> General -> Your apps -> Web App)
(() => {
  if (window.AcadexAuthInitialized) return;
  window.AcadexAuthInitialized = true;

  const firebaseConfig = {
  apiKey: "AIzaSyDAlTPzibRda5K-SpAw0mM1_fuJR0rpeEE",
  authDomain: "acadex-2a0ae.firebaseapp.com",
  projectId: "acadex-2a0ae",
  storageBucket: "acadex-2a0ae.firebasestorage.app",
  messagingSenderId: "337009149669",
  appId: "1:337009149669:web:b62352defd8b0f0d51f60c",
  measurementId: "G-4RY0VM1T19"
  };

// Initialize Firebase
  firebase.initializeApp(firebaseConfig);

  const auth = firebase.auth();
  const db = typeof firebase.firestore === "function" ? firebase.firestore() : null;
  const storage = typeof firebase.storage === "function" ? firebase.storage() : null;
  const loginBtn = document.getElementById("login-btn");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const errorMsg = document.getElementById("error-message");
  const isLocalhost =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname.endsWith(".local");
  const DEFAULT_API_BASE_URL = isLocalhost
    ? `http://${window.location.hostname}:8080/api`
    : `${window.location.origin}/api`;
  const AUTH_API_BASE_URL = window.ACADEX_API_BASE_URL || DEFAULT_API_BASE_URL;

/**
 * AUTHORIZED AUTH LOGIN PROTOCOL
 * Centralized authentication engine for institutional infiltration
 */
  async function authLogin(email, password) {
  try {
    // 1. Sign in with Firebase
    const userCredential = await auth.signInWithEmailAndPassword(email, password);
    const user = userCredential.user;

    // 2. Get ID Token
    const idToken = await user.getIdToken();

    // 3. Verify with our backend and get user role
    const response = await fetch(`${AUTH_API_BASE_URL}/auth/me`, {
      headers: {
        "Authorization": `Bearer ${idToken}`
      }
    });

    if (!response.ok) throw new Error("Could not fetch user profile from Acadex backend.");

    const userData = await response.json();
    localStorage.setItem("acadex_user", JSON.stringify(userData));
    return userData;
  } catch (error) {
    throw error;
  }
  }

  if (loginBtn) {
    loginBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      const email = emailInput.value;
      const password = passwordInput.value;

      // Clear error message
      errorMsg.style.display = "none";
      loginBtn.innerText = "Authenticating...";
      loginBtn.disabled = true;

      try {
        // 1. Sign in with Firebase
        const userCredential = await auth.signInWithEmailAndPassword(email, password);
        const user = userCredential.user;

        // 2. Get ID Token
        const idToken = await user.getIdToken();

        // 3. Verify with our backend and get user role
        const response = await fetch(`${AUTH_API_BASE_URL}/auth/me`, {
          headers: {
            "Authorization": `Bearer ${idToken}`
          }
        });

        if (!response.ok) throw new Error("Could not fetch user profile from Acadex backend.");

        const userData = await response.json();
        const role = userData.role;

        // 4. Redirect based on role
        localStorage.setItem("acadex_user", JSON.stringify(userData));

        if (role === "admin") {
          window.location.href = "dashboards/admin-dashboard.html";
        } else if (role === "faculty") {
          window.location.href = "dashboards/faculty-dashboard.html";
        } else {
          window.location.href = "dashboards/student-dashboard.html";
        }

      } catch (error) {
        console.error(error);
        errorMsg.innerText = error.message;
        errorMsg.style.display = "block";
        loginBtn.innerText = "Sign In";
        loginBtn.disabled = false;
      }
    });
  }

// Check session on dashboard pages
  function checkAuth() {
    auth.onAuthStateChanged((user) => {
      if (!user) {
        window.location.href = `${window.location.origin}/index.html`;
      }
    });
  }

  async function authLogout() {
    await auth.signOut();
    localStorage.removeItem("acadex_user");
    window.location.href = `${window.location.origin}/index.html`;
  }

  window.authLogin = authLogin;
  window.checkAuth = checkAuth;
  window.authLogout = authLogout;
  window.auth = auth;
  window.db = db;
  window.storage = storage;
})();
