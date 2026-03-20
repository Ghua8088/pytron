use pyo3::prelude::*;

pub enum UserEvent {
    Eval(String),
    Bind(String, PyObject),   
    Dispatch(PyObject, String, String), // Func, Seq, MethodName
    DispatchData(PyObject, String, String, String), // Func, Seq, Args, MethodName
    CallPython(PyObject, String, String, String), 
    
    Return(String, i32, String),
    SetTitle(String),
    SetSize(i32, i32, u32),
    SetBounds(i32, i32, i32, i32), // x, y, w, h
    Navigate(String),
    OpenDevtools,
    Quit,
    Minimize,
    SetMaximized(bool),
    SetVisible(bool),
    DragWindow,
    SetAlwaysOnTop(bool),
    TaskbarProgress(i32, i32, i32), // State, Value, Max
    SetResizable(bool),
    SetFullscreen(bool),
    CenterWindow,
    SetPreventClose(bool),
    SetDecorations(bool),
    OpenExternal(String),
    StateUpdate(String, String), // Key, Value (JSON)
}
