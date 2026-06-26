import React, { useState } from "react";
import { 
  X, Plus, Trash2, Upload, FileText, Settings, 
  CheckCircle2, BrainCircuit, ListOrdered, Shuffle,
  HelpCircle, ChevronDown, ChevronUp, Save, AlertCircle
} from "lucide-react";
import { GlassCard } from "../../shared/components/GlassCard";
import { API_ENDPOINTS } from "../../shared/utils/apiConfig";

interface Choice {
  choice_text: string;
  is_correct: boolean;
}

interface Question {
  question_text: string;
  question_type: string;
  points: number;
  choices: Choice[];
}

interface ExamCreatorProps {
  onClose: () => void;
  onSave: (examData: any) => Promise<boolean>;
  initialData?: any;
}



export const ExamCreator: React.FC<ExamCreatorProps> = ({ onClose, onSave, initialData }) => {
  const [title, setTitle] = useState(initialData?.title || "");
  const [description, setDescription] = useState(initialData?.description || "");
  const [courseId, setCourseId] = useState<number | string>(initialData?.course_id || "");
  const [courses, setCourses] = useState<any[]>([]);
  const [timeLimit, setTimeLimit] = useState(initialData?.time_limit || 60);
  const [attempts, setAttempts] = useState(initialData?.attempts_allowed || 1);
  const [randomize, setRandomize] = useState(initialData?.randomize_questions || false);
  const [questions, setQuestions] = useState<Question[]>(initialData?.questions || []);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isMappingAnswers, setIsMappingAnswers] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  React.useEffect(() => {
    fetchCourses();
  }, []);

  const fetchCourses = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(API_ENDPOINTS.COURSES, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      const data = await response.json();
      setCourses(data);
      if (data.length > 0 && !courseId) {
        setCourseId(data[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch courses", err);
    }
  };

  const addQuestion = () => {
    setQuestions([
      ...questions,
      {
        question_text: "",
        question_type: "mcq",
        points: 1,
        choices: [
          { choice_text: "", is_correct: false },
          { choice_text: "", is_correct: false },
          { choice_text: "", is_correct: false },
          { choice_text: "", is_correct: false },
        ]
      }
    ]);
  };

  const removeQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index));
  };

  const updateQuestionText = (index: number, text: string) => {
    const newQuestions = [...questions];
    newQuestions[index].question_text = text;
    setQuestions(newQuestions);
  };

  const addChoice = (qIndex: number) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].choices.push({ choice_text: "", is_correct: false });
    setQuestions(newQuestions);
  };

  const updateChoice = (qIndex: number, cIndex: number, text: string) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].choices[cIndex].choice_text = text;
    setQuestions(newQuestions);
  };

  const setCorrectChoice = (qIndex: number, cIndex: number) => {
    const newQuestions = [...questions];
    newQuestions[qIndex].choices.forEach((c, idx) => {
      c.is_correct = (idx === cIndex);
    });
    setQuestions(newQuestions);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsExtracting(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_ENDPOINTS.EXAMS}/extract`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData,
      });
      const data = await response.json();
      if (Array.isArray(data)) {
        // Ensure all extracted questions have 4 choices if they don't
        const formatted = data.map(q => ({
            ...q,
            choices: q.choices.length < 4 
              ? [...q.choices, ...Array(4 - q.choices.length).fill(0).map(() => ({ choice_text: "", is_correct: false }))]
              : q.choices
        }));
        setQuestions([...questions, ...formatted]);
      }
    } catch (err) {
      console.error("Extraction failed", err);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleAnswerKeyUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || questions.length === 0) return;

    setIsMappingAnswers(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`${API_ENDPOINTS.EXAMS}/extract-answers`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData,
      });
      const answerMap = await response.json(); // e.g. { "1": "A", "2": "C" }
      
      const updatedQuestions = [...questions];
      Object.entries(answerMap).forEach(([qNum, ansChar]) => {
          const qIdx = parseInt(qNum) - 1;
          const choiceIdx = (ansChar as string).charCodeAt(0) - 65; // A=0, B=1, ...
          
          if (updatedQuestions[qIdx] && updatedQuestions[qIdx].choices[choiceIdx]) {
              updatedQuestions[qIdx].choices.forEach((c, idx) => {
                  c.is_correct = (idx === choiceIdx);
              });
          }
      });
      setQuestions(updatedQuestions);
    } catch (err) {
        console.error("Mapping failed", err);
    } finally {
        setIsMappingAnswers(false);
    }
  };

  const handleSubmit = (status: "draft" | "published") => {
    setError("");
    
    if (!title.trim()) {
        setError("Exam title is required.");
        return;
    }

    if (!courseId || isNaN(courseId)) {
        setError("Please select a classroom.");
        return;
    }
    
    if (questions.length === 0) {
        setError("Please add at least one question.");
        return;
    }
    
    // Verification: all questions must have a correct answer selected
    const unselectedIndices = questions
      .map((q, i) => q.choices.some(c => c.is_correct) ? -1 : i)
      .filter(i => i !== -1);
      
    if (unselectedIndices.length > 0) {
        setError(`Please select correct answers for questions: ${unselectedIndices.map(i => i + 1).join(", ")}`);
        return;
    }

    const examData = {
      title,
      description,
      course_id: courseId,
      time_limit: timeLimit,
      attempts_allowed: attempts,
      randomize_questions: randomize,
      status: status,
      questions
    };
    
    setIsSaving(true);
    onSave(examData).then(success => {
        if (!success) {
            setError("Failed to save the exam. Please try again.");
            setIsSaving(false);
        }
        // If success, ExamsPage will close us.
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-5xl max-h-[90vh] bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b flex items-center justify-between bg-slate-50">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: "var(--color-brand-blue)" }}>
              <BrainCircuit size={22} /> {initialData ? "Edit Online Exam" : "Create New Online Exam"}
            </h2>
            <p className="text-sm text-slate-500">
              {initialData ? "Update the exam settings and questions below." : "Configure exam settings and add questions manually or via upload."}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Settings */}
          <div className="space-y-6">
            <section className="space-y-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <Settings size={14} /> Exam Configuration
              </h3>
              
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-semibold mb-1 block text-slate-600">Exam Title <span className="text-red-500">*</span></label>
                  <input 
                    type="text" 
                    className={`form-input text-sm ${!title && error.includes("title") ? "border-red-500" : ""}`} 
                    placeholder="e.g. Mid-Term Assessment"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    required
                  />
                </div>
                
                <div>
                  <label className="text-xs font-semibold mb-1 block text-slate-600">Assign to Class <span className="text-red-500">*</span></label>
                  <select 
                    className="form-input text-sm bg-white"
                    value={courseId}
                    onChange={(e) => setCourseId(parseInt(e.target.value))}
                  >
                    {courses.length === 0 && <option value="">Loading classes...</option>}
                    {courses.map(course => (
                      <option key={course.id} value={course.id}>
                        {course.code} - {course.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-semibold mb-1 block text-slate-600">Time Limit (Minutes)</label>
                  <div className="flex items-center gap-3">
                    <input 
                      type="number" 
                      className="form-input text-sm" 
                      value={timeLimit}
                      onChange={(e) => setTimeLimit(parseInt(e.target.value))}
                    />
                    <span className="text-xs text-slate-400 shrink-0">mins</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-semibold mb-1 block text-slate-600">Attempts</label>
                    <input 
                      type="number" 
                      className="form-input text-sm" 
                      value={attempts}
                      onChange={(e) => setAttempts(parseInt(e.target.value))}
                    />
                  </div>
                  <div className="flex flex-col justify-end pb-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input 
                        type="checkbox" 
                        className="rounded text-blue-600 focus:ring-blue-500"
                        checked={randomize}
                        onChange={(e) => setRandomize(e.target.checked)}
                      />
                      <span className="text-xs font-semibold text-slate-600">Randomize</span>
                    </label>
                  </div>
                </div>
              </div>
            </section>

            <section className="p-4 rounded-2xl bg-blue-50 border border-blue-100 space-y-4">
              <h4 className="text-xs font-bold text-blue-700 flex items-center gap-2">
                <Upload size={14} /> Smart Import
              </h4>
              
              <div className="space-y-3">
                <div>
                    <p className="text-[10px] text-blue-600/70 mb-1.5 font-bold uppercase tracking-tight">Step 1: Upload Questions</p>
                    <label className="btn btn-primary w-full text-xs py-2 cursor-pointer flex items-center justify-center gap-2 shadow-sm">
                        <FileText size={12} /> {isExtracting ? "Parsing..." : "Select Question Paper"}
                        <input type="file" className="hidden" accept=".pdf,.docx" onChange={handleFileUpload} disabled={isExtracting} />
                    </label>
                </div>

                <div className={questions.length === 0 ? "opacity-40 pointer-events-none" : ""}>
                    <p className="text-[10px] text-blue-600/70 mb-1.5 font-bold uppercase tracking-tight">Step 2: Upload Answer Key</p>
                    <label className="btn border-2 border-blue-200 text-blue-700 bg-white hover:bg-blue-50 w-full text-xs py-2 cursor-pointer flex items-center justify-center gap-2 shadow-sm">
                        <CheckCircle2 size={12} /> {isMappingAnswers ? "Mapping..." : "Select Answer Key"}
                        <input type="file" className="hidden" accept=".pdf,.docx" onChange={handleAnswerKeyUpload} disabled={isMappingAnswers || questions.length === 0} />
                    </label>
                </div>
              </div>
              <p className="text-[9px] text-blue-600/60 leading-tight italic">
                * Answer key should follow format: 1. A, 2. C...
              </p>
            </section>
          </div>

          {/* Right Column: Questions */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400">
                Questions ({questions.length})
              </h3>
              <button 
                onClick={addQuestion}
                className="btn btn-outline text-xs py-1.5 px-3 flex items-center gap-1.5"
              >
                <Plus size={14} /> Add Question
              </button>
            </div>

            {error && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-100 flex items-center gap-2 text-red-600 text-xs animate-shake">
                    <AlertCircle size={14} />
                    <span>{error}</span>
                </div>
            )}

            {questions.length === 0 ? (
              <div className="h-64 flex flex-col items-center justify-center border-2 border-dashed border-slate-200 rounded-3xl text-slate-400 bg-slate-50/50">
                <HelpCircle size={40} strokeWidth={1} className="mb-2" />
                <p className="text-sm">No questions added yet.</p>
                <p className="text-xs">Start by adding one manually or uploading a file.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {questions.map((q, qi) => (
                  <GlassCard key={qi} padding="md" className="border border-slate-200/50 relative group">
                    <button 
                      onClick={() => removeQuestion(qi)}
                      className="absolute top-4 right-4 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 size={16} />
                    </button>
                    
                    <div className="flex gap-4">
                      <span className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-500">
                        {qi + 1}
                      </span>
                      <div className="flex-1 space-y-4">
                        <textarea 
                          className="form-input text-sm w-full min-h-[80px] bg-transparent border-0 border-b rounded-none focus:ring-0 p-0"
                          placeholder="Type your question here..."
                          value={q.question_text}
                          onChange={(e) => updateQuestionText(qi, e.target.value)}
                        />
                        
                        <div className="space-y-2">
                          {q.choices.map((choice, ci) => (
                            <div key={ci} className="flex items-center gap-3">
                              <button 
                                onClick={() => setCorrectChoice(qi, ci)}
                                className={`w-6 h-6 rounded-full flex items-center justify-center transition-colors ${
                                  choice.is_correct ? "bg-green-500 text-white" : "bg-slate-100 text-slate-300 hover:bg-slate-200"
                                }`}
                              >
                                <CheckCircle2 size={14} />
                              </button>
                              <input 
                                type="text"
                                className={`flex-1 text-xs py-2 px-3 rounded-xl border transition-all ${
                                  choice.is_correct ? "bg-green-50/50 border-green-200 text-green-700 shadow-sm font-semibold" : "bg-slate-50 border-transparent focus:bg-white focus:border-blue-300"
                                }`}
                                placeholder={`Option ${String.fromCharCode(65 + ci)}`}
                                value={choice.choice_text}
                                onChange={(e) => updateChoice(qi, ci, e.target.value)}
                              />
                            </div>
                          ))}
                          <button 
                            onClick={() => addChoice(qi)}
                            className="text-[10px] font-bold text-blue-500 mt-1 hover:underline flex items-center gap-1"
                          >
                            <Plus size={10} /> Add Option
                          </button>
                        </div>
                      </div>
                    </div>
                  </GlassCard>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t flex items-center justify-end gap-3 bg-slate-50">
          <button onClick={onClose} className="btn btn-outline px-6 py-2">Cancel</button>
          
          <button 
            onClick={() => handleSubmit("draft")}
            className={`btn border-2 border-slate-200 text-slate-600 bg-white hover:bg-slate-50 px-6 py-2 font-bold flex items-center gap-2 transition-all ${isSaving ? 'opacity-70 cursor-not-allowed' : ''}`}
            disabled={isSaving}
          >
            <Save size={18} /> Save as Draft
          </button>

          <button 
            onClick={() => handleSubmit("published")}
            className={`btn btn-primary px-10 py-2 font-bold flex items-center gap-2 shadow-lg hover:shadow-xl active:scale-95 transition-all ${isSaving ? 'opacity-70 cursor-not-allowed' : ''}`}
            disabled={questions.length === 0 || isSaving}
          >
            {isSaving ? (
                <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Saving...
                </>
            ) : (
                <>
                    <CheckCircle2 size={18} /> Save & Publish Exam
                </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
