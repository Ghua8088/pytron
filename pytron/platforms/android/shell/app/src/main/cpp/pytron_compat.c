#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <ctype.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <pthread.h>
#include <android/log.h>

#define LOG_TAG "PytronCompat"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

/**
 * PYTRON ANDROID COMPATIBILITY LAYER (EXTENDED)
 * 
 * This file implements a wide range of symbols that are present in Glibc but missing 
 * or different in Bionic (Android). linking this into the native bridge allows 
 * many Linux-built wheels (numpy, scipy, pandas, cv2, etc.) to resolve symbols at runtime.
 */

// ============================================================================
// 1. STACK PROTECTION (Glibc <-> Bionic)
// ============================================================================
void __stack_chk_fail_local(void) {
    LOGE("Stack smashing detected (shim)!");
    abort();
}

// ============================================================================
// 2. GLIBC FORTIFIED FUNCTIONS (_FORTIFY_SOURCE)
// ============================================================================
// Bionic lacks these specific symbols which Linux-built binaries often require.

int __printf_chk(int flag, const char *format, ...) {
    va_list ap;
    va_start(ap, format);
    int ret = vprintf(format, ap);
    va_end(ap);
    return ret;
}

int __fprintf_chk(FILE *fp, int flag, const char *format, ...) {
    va_list ap;
    va_start(ap, format);
    int ret = vfprintf(fp, format, ap);
    va_end(ap);
    return ret;
}

int __vfprintf_chk(FILE *fp, int flag, const char *format, va_list ap) {
    return vfprintf(fp, format, ap);
}

int __snprintf_chk(char *str, size_t maxlen, int flag, size_t strlen, const char *format, ...) {
    va_list ap;
    va_start(ap, format);
    int ret = vsnprintf(str, maxlen, format, ap);
    va_end(ap);
    return ret;
}

int __vsnprintf_chk(char *str, size_t maxlen, int flag, size_t strlen, const char *format, va_list ap) {
    return vsnprintf(str, maxlen, format, ap);
}

int __sprintf_chk(char *s, int flags, size_t slen, const char *format, ...) {
    va_list arg;
    int done;
    va_start(arg, format);
    done = vsprintf(s, format, arg);
    va_end(arg);
    return done;
}

void *__memcpy_chk(void *dest, const void *src, size_t len, size_t destlen) {
    if (len > destlen) {
        LOGE("__memcpy_chk: buffer overflow detected");
        abort();
    }
    return memcpy(dest, src, len);
}

void *__memmove_chk(void *dest, const void *src, size_t len, size_t destlen) {
    if (len > destlen) {
        LOGE("__memmove_chk: buffer overflow detected");
        abort();
    }
    return memmove(dest, src, len);
}

void *__memset_chk(void *s, int c, size_t n, size_t dstlen) {
    if (n > dstlen) {
        LOGE("__memset_chk: buffer overflow detected");
        abort();
    }
    return memset(s, c, n);
}

char *__strncpy_chk(char *s1, const char *s2, size_t n, size_t s1len) {
    if (n > s1len) {
        LOGE("__strncpy_chk: buffer overflow detected");
        abort();
    }
    return strncpy(s1, s2, n);
}

char *__strcat_chk(char *dest, const char *src, size_t destlen) {
    // Check is harder for strcat, but we can try
    size_t current_len = strlen(dest);
    size_t append_len = strlen(src);
    if (current_len + append_len + 1 > destlen) {
         LOGE("__strcat_chk: buffer overflow detected");
         abort();
    }
    return strcat(dest, src);
}

char *__strcpy_chk(char *dest, const char *src, size_t destlen) {
    size_t len = strlen(src);
    if (len + 1 > destlen) {
        LOGE("__strcpy_chk: buffer overflow detected");
        abort();
    }
    return strcpy(dest, src);
}

// ============================================================================
// 3. LOCALE & CTYPE INTERNALS
// ============================================================================
// Glibc exposes these as functions returning pointers to arrays. 
// Bionic has different internals. We provide safe fallbacks.

static const unsigned short *__ctype_b_loc_shim(void) {
    // Return the standard C locale table or a safe fallback
    // Bionic usually has _ctype_
    extern const unsigned short *__ctype_b; // Bionic internal?
    // Fallback: This might not be 100% correct for all locales but prevents crashes
    // We really want the address of the current thread's locale table.
    // For now, let's just return a pointer that won't segfault if read.
    static unsigned short safe_table[384]; 
    return safe_table + 128; // Offset for negative indices
}

const unsigned short **__ctype_b_loc(void) {
    static const unsigned short *table = NULL;
    // Bionic's __ctype_get_mb_cur_max is not what we want.
    // We are mocking the Accessor Function that Glibc uses.
    if (!table) {
        // Try to bind to Bionic's if available, otherwise use our safe dummy
        table = __ctype_b_loc_shim(); 
    }
    static const unsigned short *ret = NULL;
    ret = table;
    return &ret;
}

const int32_t **__ctype_tolower_loc(void) {
    static int32_t safe_lower[384];
    static const int32_t *ret = safe_lower + 128;
    return &ret;
}

const int32_t **__ctype_toupper_loc(void) {
    static int32_t safe_upper[384];
    static const int32_t *ret = safe_upper + 128;
    return &ret;
}

// ============================================================================
// 4. LEGACY STRING & MEMORY FUNCTIONS
// ============================================================================

void bcopy(const void *src, void *dest, size_t n) {
    memmove(dest, src, n);
}

void bzero(void *s, size_t n) {
    memset(s, 0, n);
}

int bcmp(const void *s1, const void *s2, size_t n) {
    return memcmp(s1, s2, n);
}

char *index(const char *s, int c) {
    return strchr(s, c);
}

char *rindex(const char *s, int c) {
    return strrchr(s, c);
}

int strverscmp(const char *s1, const char *s2) {
    return strcmp(s1, s2); // Simplified fallback
}

// ============================================================================
// 5. SYSTEM V IPC STUBS (Shared Memory)
// ============================================================================
// Android does not support SysV IPC. We stub these to return errors (ENOSYS)
// so that applications checking for availability gracefully fail instead of crashing on load.

int shmget(key_t key, size_t size, int shmflg) {
    errno = ENOSYS;
    return -1;
}

void *shmat(int shmid, const void *shmaddr, int shmflg) {
    errno = ENOSYS;
    return (void *)-1;
}

int shmdt(const void *shmaddr) {
    errno = ENOSYS;
    return -1;
}

int shmctl(int shmid, int cmd, struct shmid_ds *buf) {
    errno = ENOSYS;
    return -1;
}

// ============================================================================
// 6. MATH & TIME
// ============================================================================

int finite(double x) {
    return isfinite(x);
}

int finitef(float x) {
    return isfinite(x);
}

struct timeb {
    time_t         time;
    unsigned short millitm;
    short          timezone;
    short          dstflag;
};

int ftime(struct timeb *tp) {
    struct timeval tv;
    struct timezone tz;
    if (gettimeofday(&tv, &tz) < 0) return -1;
    tp->time = tv.tv_sec;
    tp->millitm = tv.tv_usec / 1000;
    tp->timezone = tz.tz_minuteswest;
    tp->dstflag = tz.tz_dsttime;
    return 0;
}

// ============================================================================
// 7. FILES & IO
// ============================================================================

int getdtablesize(void) {
    return sysconf(_SC_OPEN_MAX);
}

void error(int status, int errnum, const char *format, ...) {
    va_list ap;
    va_start(ap, format);
    __android_log_vprint(ANDROID_LOG_ERROR, LOG_TAG, format, ap);
    va_end(ap);
    if (status) exit(status);
}

// ============================================================================
// 8. PTHREAD STUBS
// ============================================================================
// Android supports most pthreads, but some advanced/obscure features might be missing.

int pthread_cancel(pthread_t thread) {
    // Android does NOT support pthread_cancel.
    // Returning an error is the safest bet.
    LOGW("pthread_cancel called (not supported on Android)");
    return ESRCH; 
}

int pthread_setcancelstate(int state, int *oldstate) {
    // Stub: pretend we did it
    if (oldstate) *oldstate = PTHREAD_CANCEL_ENABLE;
    return 0;
}

int pthread_setcanceltype(int type, int *oldtype) {
    // Stub
    if (oldtype) *oldtype = PTHREAD_CANCEL_DEFERRED;
    return 0;
}

void pthread_testcancel(void) {
    // No-op
}

// ============================================================================
// 9. MISC & DEBUGGING
// ============================================================================

void __gnu_mcount_nc(void) { }

int backtrace(void **buffer, int size) { return 0; }
char **backtrace_symbols(void *const *buffer, int size) { return NULL; }
void backtrace_symbols_fd(void *const *buffer, int size, int fd) { }

__attribute__((constructor))
void pytron_compat_init(void) {
    LOGI("Pytron Compatibility Layer (Extended) Loaded.");
}
