#include <jni.h>
#include <string>
#include <android/log.h>
#include <Python.h>
#include <dlfcn.h>
#include <vector>
#include <unistd.h>
#include <fcntl.h>
#include <pthread.h>

#define LOG_TAG "PytronNative"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

static JavaVM* gJavaVM = nullptr;
static jobject gMainActivity = nullptr;

// --- NATIVE LOG REDIRECTION ---
static int pipe_stdout[2];
static int pipe_stderr[2];
static pthread_t thread_stdout;
static pthread_t thread_stderr;

void* log_reader_thread(void* arg) {
    int* fd = (int*)arg;
    char buffer[1024];
    ssize_t r;
    while ((r = read(fd[0], buffer, sizeof(buffer) - 1)) > 0) {
        buffer[r] = '\0';
        __android_log_write(ANDROID_LOG_INFO, "PythonOutput", buffer);
    }
    return nullptr;
}

void start_logger() {
    pipe(pipe_stdout);
    pipe(pipe_stderr);
    dup2(pipe_stdout[1], STDOUT_FILENO);
    dup2(pipe_stderr[1], STDERR_FILENO);
    pthread_create(&thread_stdout, nullptr, log_reader_thread, &pipe_stdout);
    pthread_create(&thread_stderr, nullptr, log_reader_thread, &pipe_stderr);
}
// -----------------------------

// Helper to send message to Java
static PyObject* py_send_to_android(PyObject* self, PyObject* args) {
    const char* message;
    if (!PyArg_ParseTuple(args, "s", &message)) {
        return NULL;
    }

    JNIEnv* env;
    bool needsDetach = false;
    int envStat = gJavaVM->GetEnv((void**)&env, JNI_VERSION_1_6);
    if (envStat == JNI_EDETACHED) {
        gJavaVM->AttachCurrentThread(&env, NULL);
        needsDetach = true;
    }

    if (gMainActivity && env) {
        jclass cls = env->GetObjectClass(gMainActivity);
        jmethodID mid = env->GetMethodID(cls, "onMessageFromPython", "(Ljava/lang/String;)Ljava/lang/String;");
        if (mid) {
            jstring jStr = env->NewStringUTF(message);
            jobject result = env->CallObjectMethod(gMainActivity, mid, jStr);
            env->DeleteLocalRef(jStr);
            if (env->ExceptionCheck()) {
                env->ExceptionDescribe();
                env->ExceptionClear();
            }
        }
    }
    if (needsDetach) gJavaVM->DetachCurrentThread();
    Py_RETURN_NONE;
}

static PyMethodDef AndroidMethods[] = {
    {"send_to_android", py_send_to_android, METH_VARARGS, "Send message to Android layer"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef androidmodule = {
    PyModuleDef_HEAD_INIT, "_pytron_android", NULL, -1, AndroidMethods
};

PyMODINIT_FUNC PyInit__pytron_android(void) {
    return PyModule_Create(&androidmodule);
}

extern "C" JNIEXPORT void JNICALL
Java_com_pytron_shell_MainActivity_startPython(JNIEnv* env, jobject thiz, jstring homePath) {
    if (gMainActivity) env->DeleteGlobalRef(gMainActivity);
    gMainActivity = env->NewGlobalRef(thiz);

    const char* path = env->GetStringUTFChars(homePath, 0);
    LOGI("Starting Python configuration with home: %s", path);

    // ==========================================================
    // 1. FIX FILE DESCRIPTORS & START NATIVE LOGGER
    // ==========================================================
    start_logger();
    // ==========================================================

    // 2. ENVIRONMENT SETUP
    setenv("PYTHONHOME", path, 1);
    setenv("PYTHONUNBUFFERED", "1", 1); 
    setenv("PYTHONUTF8", "1", 1);
    setenv("PYTHON_PLATFORM","android",1);
    
    std::string base = std::string(path);
    std::string libPath = base + "/Lib";
    std::string sitePath = base + "/site-packages";
    std::string zipPath = base + "/python314.zip";

    // DLOPEN libpython globally to ensure C extensions can find symbols
    void* handle = dlopen("libpython3.14.so", RTLD_NOW | RTLD_GLOBAL);
    if (!handle) LOGE("Could not dlopen libpython3.14.so: %s", dlerror());
    else LOGI("Successfully loaded libpython3.14.so globally");

    // --- CONFIGURATION ---
    PyStatus status;
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);

    // We handle IO via pipes now, but let Python think it has stdio if needed
    config.configure_c_stdio = 1; 
    config.parse_argv = 0;
    config.install_signal_handlers = 0; // Prevent Python from crashing JVM on signals

    wchar_t *wpath = Py_DecodeLocale(path, NULL);
    status = PyConfig_SetString(&config, &config.program_name, wpath);
    status = PyConfig_SetString(&config, &config.home, wpath);

    // MODULE SEARCH PATHS
    config.module_search_paths_set = 1;

    wchar_t *wBase = Py_DecodeLocale(base.c_str(), NULL);
    wchar_t *wLib = Py_DecodeLocale(libPath.c_str(), NULL);
    wchar_t *wSite = Py_DecodeLocale(sitePath.c_str(), NULL);
    wchar_t *wZip = Py_DecodeLocale(zipPath.c_str(), NULL);

    PyWideStringList_Append(&config.module_search_paths, wBase);
    PyWideStringList_Append(&config.module_search_paths, wLib);

    std::string dynPath = libPath + "/lib-dynload";
    wchar_t *wDyn = Py_DecodeLocale(dynPath.c_str(), NULL);
    PyWideStringList_Append(&config.module_search_paths, wDyn);

    PyWideStringList_Append(&config.module_search_paths, wZip);
    PyWideStringList_Append(&config.module_search_paths, wSite);

    // Register embedded module
    if (PyImport_AppendInittab("_pytron_android", PyInit__pytron_android) == -1) {
        LOGE("Failed to add _pytron_android to builtins");
    }

    LOGI("Calling Py_InitializeFromConfig...");
    status = Py_InitializeFromConfig(&config);

    if (PyStatus_Exception(status)) {
        LOGE("FATAL: Py_InitializeFromConfig failed.");
        if (status.err_msg) LOGE("Python Config Error: %s", status.err_msg);
    } else {
        LOGI("Py_Initialize success!");

        // Run Main
        std::string runCmd =
            "import sys, os\n"
            "try:\n"
            "    import main\n"
            "    if hasattr(main, 'main'): main.main()\n"
            "except Exception as e:\n"
            "    import traceback\n"
            "    traceback.print_exc()\n"
            "    err_msg = 'Python Crash: ' + str(e)\n"
            "    import _pytron_android, json\n"
            "    _pytron_android.send_to_android(json.dumps({'method': 'message_box', 'args': {'title': 'Crash', 'message': err_msg}}))\n";

        PyRun_SimpleString(runCmd.c_str());
    }

    PyConfig_Clear(&config);
    env->ReleaseStringUTFChars(homePath, path);
    PyMem_Free(wpath);
    PyMem_Free(wBase);
    PyMem_Free(wLib);
    PyMem_Free(wSite);
    PyMem_Free(wZip);
    PyMem_Free(wDyn);
}

extern "C" JNIEXPORT void JNICALL
Java_com_pytron_shell_MainActivity_sendToPython(JNIEnv* env, jobject thiz, jstring message) {
    if (!Py_IsInitialized()) return;
    PyGILState_STATE gstate = PyGILState_Ensure();
    const char* msg = env->GetStringUTFChars(message, 0);
    
    // LOGI("Received message for Python: %s", msg);

    // Call pytron.bindings.dispatch_android_message(msg)
    PyObject* bindings = PyImport_ImportModule("pytron.bindings");
    if (bindings) {
        PyObject* func = PyObject_GetAttrString(bindings, "dispatch_android_message");
        if (func && PyCallable_Check(func)) {
            PyObject* args = PyTuple_Pack(1, PyUnicode_FromString(msg));
            PyObject* result = PyObject_CallObject(func, args);
            Py_XDECREF(result);
            Py_DECREF(args);
            Py_DECREF(func);
        } else {
             if (PyErr_Occurred()) PyErr_Print();
             LOGE("Could not find dispatch_android_message in pytron.bindings");
        }
        Py_DECREF(bindings);
    } else {
         if (PyErr_Occurred()) PyErr_Print();
         LOGE("Could not import pytron.bindings");
    }

    env->ReleaseStringUTFChars(message, msg);
    PyGILState_Release(gstate);
}

extern "C" JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm, void* reserved) {
    gJavaVM = vm;
    return JNI_VERSION_1_6;
}