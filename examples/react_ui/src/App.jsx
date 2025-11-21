import { useState } from 'react'
import './App.css'
import pytron from 'pytron-client'

function TitleBar() {
  return (
    <div className="titlebar">
      <div className="titlebar-drag-region">
        Calculator
      </div>
      <div className="titlebar-controls">
        <button className="titlebar-btn" onClick={() => pytron.minimize()}>─</button>
        <button className="titlebar-btn close" onClick={() => pytron.close()}>✕</button>
      </div>
    </div>
  );
}

function App() {
  const [display, setDisplay] = useState('0');
  const [expression, setExpression] = useState('');
  const [waitingForOperand, setWaitingForOperand] = useState(false);

  const inputDigit = (digit) => {
    if (waitingForOperand) {
      setDisplay(String(digit));
      setWaitingForOperand(false);
    } else {
      setDisplay(display === '0' ? String(digit) : display + digit);
    }
    setExpression(expression + digit);
  };

  const inputDot = () => {
    if (waitingForOperand) {
      setDisplay('0.');
      setWaitingForOperand(false);
      setExpression(expression + '0.');
    } else if (display.indexOf('.') === -1) {
      setDisplay(display + '.');
      setExpression(expression + '.');
    }
  };

  const clear = () => {
    setDisplay('0');
    setExpression('');
    setWaitingForOperand(false);
  };

  const performOperation = (op) => {
    // Visual update for display (optional, usually calculators just show the number)
    // But we need to track the expression for the backend

    // If last char was an operator, replace it
    const lastChar = expression.slice(-1);
    if (['+', '-', '*', '/'].includes(lastChar)) {
      setExpression(expression.slice(0, -1) + op);
    } else {
      setExpression(expression + op);
    }

    setWaitingForOperand(true);
  };

  const handleEqual = async () => {
    try {
      const result = await pytron.calculate(expression);
      setDisplay(String(result));
      setExpression(String(result)); // Allow chaining calculations
      setWaitingForOperand(true);
    } catch (e) {
      console.error(e);
      setDisplay('Error');
      setExpression('');
    }
  };

  return (
    <div className="app-container">
      <TitleBar />
      <div className="calculator">
        <div className="display">{display}</div>
        <div className="keypad">
          <button className="key function" onClick={clear}>AC</button>
          <button className="key function" onClick={() => setDisplay(String(parseFloat(display) * -1))}>+/-</button>
          <button className="key function" onClick={() => performOperation('%')}>%</button>
          <button className="key operator" onClick={() => performOperation('/')}>÷</button>

          <button className="key" onClick={() => inputDigit(7)}>7</button>
          <button className="key" onClick={() => inputDigit(8)}>8</button>
          <button className="key" onClick={() => inputDigit(9)}>9</button>
          <button className="key operator" onClick={() => performOperation('*')}>×</button>

          <button className="key" onClick={() => inputDigit(4)}>4</button>
          <button className="key" onClick={() => inputDigit(5)}>5</button>
          <button className="key" onClick={() => inputDigit(6)}>6</button>
          <button className="key operator" onClick={() => performOperation('-')}>−</button>

          <button className="key" onClick={() => inputDigit(1)}>1</button>
          <button className="key" onClick={() => inputDigit(2)}>2</button>
          <button className="key" onClick={() => inputDigit(3)}>3</button>
          <button className="key operator" onClick={() => performOperation('+')}>+</button>

          <button className="key zero" onClick={() => inputDigit(0)}>0</button>
          <button className="key" onClick={inputDot}>.</button>
          <button className="key operator" onClick={handleEqual}>=</button>
        </div>
      </div>
    </div>
  )
}

export default App
