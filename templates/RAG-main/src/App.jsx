import React, { useState, useEffect, useRef } from 'react';
//hehe
export default function Rag() {
  const [isResponseScreen, setIsResponseScreen] = useState(false);
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);

  // Default responses for suggested questions
  const defaultResponses = {
    "Which gaming laptop should I buy?": 
      "To recommend the best gaming laptop, it helps to know your specific needs and preferences. Could you share details like:\nBudget - How much are you willing to spend?\nGame Types - Do you play graphically intense AAA games, or are your needs lighter (e.g., indie or esports titles)?\nScreen Size - Do you prefer portability (smaller screen) or an immersive experience (larger screen)?\nPerformance Preferences - Do you prioritize raw power (CPU, GPU) or features like RGB lighting, a mechanical keyboard, or a high-refresh-rate screen?\nOnce I have this info, I can suggest gaming laptops that match your preferences!",
    
    "What is the lastest Iphone right now?": 
      "Iphone 16, Iphone 16 pro and Iphone 16 promax",
    
    "Compare between Dell and Macbook? Which one is better?": 
      "Lenovo",
    
    "Which laptop is the most suitable for Computer Science?": 
      "Ofc Lenovo."
  };

  // Scroll to bottom of messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Function to handle sending messages
  const sendMessage = () => {
    if (message.trim() === '') return;
    
    // Add user message
    const newMessages = [...messages, { type: 'userMsg', text: `You: ${message}` }];
    setMessages(newMessages);
    
    // Simulate AI response with delay
    setTimeout(() => {
      let response = "I'm not sure how to respond to that. Could you ask something else?";
      
      // Check for predefined responses
      Object.keys(defaultResponses).forEach(key => {
        if (message.toLowerCase().includes(key.toLowerCase().substring(0, 10))) {
          response = defaultResponses[key];
        }
      });
      
      setMessages([...newMessages, { type: 'responseMsg', text: response }]);
    }, 1000);
    
    // Clear input
    setMessage('');
  };

  // Function to handle preset questions
  const handlePresetQuestion = (question) => {
    setIsResponseScreen(true);
    
    // Add user message
    const newMessages = [{ type: 'userMsg', text: `You: ${question}` }];
    setMessages(newMessages);
    
    // Add AI response with delay
    setTimeout(() => {
      setMessages([
        ...newMessages,
        { type: 'responseMsg', text: defaultResponses[question] }
      ]);
    }, 800);
  };

  // Function to start a new chat
  const newChat = () => {
    setMessages([]);
    setIsResponseScreen(false);
  };

  return (
    <div className="container w-screen min-h-screen overflow-x-hidden bg-[#FFFFFF] text-white">
      {isResponseScreen ? (
        <div className="h-[80vh] flex flex-col">
          <div className="header pt-[25px] flex items-center justify-between w-full px-4 md:px-[100px] lg:px-[300px]">
            <h2 className="text-2xl">AssistMe</h2>
            <button
              id="newChatBtn"
              className="bg-[#181818] p-[10px] rounded-[30px] cursor-pointer text-[14px] px-[20px]"
              onClick={newChat}
            >
              New Chat
            </button>
          </div>
          
          <div className="messages flex-1 overflow-y-auto px-4 md:px-[100px] lg:px-[300px] py-6 space-y-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`${
                  msg.type === 'userMsg' 
                    ? 'bg-[#1E1E1E] self-end' 
                    : 'bg-[#2A2A2A]'
                } p-3 rounded-lg max-w-[80%] ${
                  msg.type === 'userMsg' ? 'ml-auto' : 'mr-auto'
                }`}
              >
                {msg.text}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>
      ) : (
        <div className="middle h-[80vh] flex items-center flex-col justify-center">
          <h1 className="text-4xl mb-2" style={{ color: '#FFB804' }}>Hello!</h1>
          <p className="text-2xl mb-6" style={{ color: '#BE8B52' }}>How can I help you today?</p>
          
          <div className="boxes mt-[30px] grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 px-4 w-full max-w-6xl">
            <div
              className="card rounded-lg cursor-pointer transition-all hover:bg-[#201f1f] px-[20px] relative min-h-[20vh] bg-[#0D3B2F] p-[15px] flex flex-col justify-between"
              onClick={() => handlePresetQuestion("Which gaming laptop should I buy?")}
            >
              <p className="text-[18px] text-white">Which gaming laptop should I buy?</p>
            </div>
            
            <div
              className="card rounded-lg cursor-pointer transition-all hover:bg-[#201f1f] px-[20px] relative min-h-[20vh] bg-[#0D3B2F] p-[15px] flex flex-col justify-between"
              onClick={() => handlePresetQuestion("What is the lastest Iphone right now?")}
            >
              <p className="text-[18px] text-white">What is the lastest Iphone right now?</p>
            </div>
            
            <div
              className="card rounded-lg cursor-pointer transition-all hover:bg-[#201f1f] px-[20px] relative min-h-[20vh] bg-[#0D3B2F] p-[15px] flex flex-col justify-between"
              onClick={() => handlePresetQuestion("Compare between Dell and Macbook? Which one is better?")}
            >
              <p className="text-[18px] text-white">Compare between Dell and Macbook? Which one is better?</p>
            </div>
            
            <div
              className="card rounded-lg cursor-pointer transition-all hover:bg-[#201f1f] px-[20px] relative min-h-[20vh] bg-[#0D3B2F] p-[15px] flex flex-col justify-between"
              onClick={() => handlePresetQuestion("Which laptop is the most suitable for Computer Science?")}
            >
              <p className="text-[18px] text-white">Which laptop is the most suitable for Computer Science?</p>
            </div>
          </div>
        </div>
      )}
      
      <div className="bottom w-full flex flex-col items-center py-4">
        <div className="inputBox w-[90%] md:w-[70%] lg:w-[60%] text-[15px] py-[7px] flex items-center bg-[#181818] rounded-[30px]">
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            type="text"
            className="p-[10px] pl-[15px] bg-transparent flex-1 outline-none border-none"
            placeholder="Write your message here..."
            id="messageBox"
          />
          {message !== "" && (
            <button 
              className="text-green-500 mr-5 cursor-pointer px-3 py-1"
              onClick={sendMessage}
            >
              Send
            </button>
          )}
        </div>
        <p className="text-gray-500 text-[14px] my-4 text-center px-4">
        ChatWithMe may make mistakes. Please check important information.
        </p>
      </div>
    </div>
  );
}