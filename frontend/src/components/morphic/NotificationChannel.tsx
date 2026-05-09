import { useState } from "react";
import { Settings, CheckCircle, AlertCircle, TestTube } from "lucide-react";
import { api } from "@/api/client";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Monitor } from "@/types/morphic";

interface NotificationChannelProps {
  type: "NTFY" | "EMAIL" | "TELEGRAM" | "SLACK";
  name: string;
  domain: string;
  monitor: Monitor;
  onSave: (data: any) => void;
}

export function NotificationChannel({ type, name, domain, monitor, onSave }: NotificationChannelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  
  const notification = monitor.notifications?.find((n: any) => n.type === type);
  const isConfigured = notification && notification.enabled;
  
  const handleTest = async () => {
    if (!notification) return;
    
    setTesting(true);
    setTestResult(null);
    
    try {
      const result = await api.testNotification(type, notification);
      setTestResult(result);
    } catch (error) {
      setTestResult({ success: false, message: "Test failed" });
    } finally {
      setTesting(false);
    }
  };

  const getIcon = () => {
    switch (type) {
      case "NTFY": return "📱";
      case "EMAIL": return "📧";
      case "TELEGRAM": return "✈️";
      case "SLACK": return "💬";
      default: return "🔔";
    }
  };

  const getStatusColor = () => {
    if (!isConfigured) return "bg-gray-100 text-gray-600";
    return "bg-green-100 text-green-600";
  };

  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-all">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="text-2xl">{getIcon()}</div>
          <div>
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-medium">{name}</h4>
              <Badge variant="outline" className="text-xs">
                {type}
              </Badge>
              {isConfigured && (
                <Badge variant="default" className="text-xs bg-green-100 text-green-800">
                  Active
                </Badge>
              )}
            </div>
            <div className="text-sm text-muted-foreground">
              {isConfigured ? (
                type === "EMAIL" ? notification.destination :
                type === "TELEGRAM" ? `@${notification.destination}` :
                type === "NTFY" ? `ntfy.sh/${notification.destination}` :
                notification.destination
              ) : (
                "Not configured"
              )}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {isConfigured && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleTest}
              disabled={testing}
            >
              {testing ? (
                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full" />
              ) : (
                <TestTube className="h-4 w-4" />
              )}
            </Button>
          )}
          
          <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Configure {name}</DialogTitle>
              </DialogHeader>
              <ChannelConfigModal
                type={type}
                name={name}
                initialData={notification}
                onSave={(data) => {
                  onSave(data);
                  setIsOpen(false);
                }}
                onTest={async (config) => {
                  try {
                    const result = await api.testNotification(type, config);
                    setTestResult(result);
                  } catch (error) {
                    setTestResult({ success: false, message: "Test failed" });
                  }
                }}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>
      
      {testResult && (
        <div className={`mt-3 p-2 rounded text-sm ${
          testResult.success 
            ? "bg-green-100 text-green-700" 
            : "bg-red-100 text-red-700"
        }`}>
          <div className="flex items-center gap-2">
            {testResult.success ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            {testResult.message}
          </div>
        </div>
      )}
    </div>
  );
}

function ChannelConfigModal({ 
  type, 
  name, 
  initialData, 
  onSave, 
  onTest 
}: { 
  type: string; 
  name: string; 
  initialData?: any; 
  onSave: (data: any) => void; 
  onTest: (config: any) => void;
}) {
  const [dest, setDest] = useState(initialData?.destination || "");
  const [secret, setSecret] = useState(initialData?.bot_token || "");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTest = async () => {
    if (!dest) return;
    setTesting(true);
    setTestResult(null);
    
    try {
      const config: any = { destination: dest, enabled: true };
      if (secret) config.bot_token = secret;
      
      await onTest(config);
      setTestResult({ success: true, message: "Test sent successfully" });
    } catch (error) {
      setTestResult({ success: false, message: "Test failed" });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>
          {type === "EMAIL"
            ? "Email Address"
            : type === "NTFY"
              ? "Topic Name"
              : "Webhook URL / ID"}
        </Label>
        <Input
          value={dest}
          onChange={(e) => {
            const value = e.target.value;
            if (type === "NTFY") {
              // Remove spaces and convert to lowercase for NTFY topics
              setDest(value.replace(/\s+/g, '').toLowerCase());
            } else {
              setDest(value);
            }
          }}
          placeholder={
            type === "EMAIL" ? "alerts@company.com" :
            type === "NTFY" ? "morphic-alerts" :
            type === "TELEGRAM" ? "123456789 or @channel" :
            type === "SLACK" ? "#alerts" :
            "https://..."
          }
        />
        {type === "NTFY" && (
          <p className="text-xs text-muted-foreground">
            Enter an NTFY topic name. Create one at{" "}
            <a href="https://ntfy.sh" target="_blank" className="text-primary hover:underline">
              ntfy.sh
            </a>
          </p>
        )}
        {type === "TELEGRAM" && (
          <p className="text-xs text-muted-foreground">
            Enter chat ID or username. Create a bot with{" "}
            <a href="https://t.me/BotFather" target="_blank" className="text-primary hover:underline">
              @BotFather
            </a>
          </p>
        )}
        {type === "EMAIL" && (
          <p className="text-xs text-muted-foreground">
            Email address for notifications. SMTP must be configured in settings.
          </p>
        )}
        {type === "SLACK" && (
          <p className="text-xs text-muted-foreground">
            Enter channel name or webhook URL. Create webhook in Slack settings.
          </p>
        )}
      </div>

      {(type === "TELEGRAM" || type === "SLACK") && (
        <div className="space-y-1.5">
          <Label>
            {type === "TELEGRAM" ? "Bot Token" : "Webhook URL"}
          </Label>
          <Input
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder={
              type === "TELEGRAM" 
                ? "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
                : "https://hooks.slack.com/services/..."
            }
          />
        </div>
      )}

      {testResult && (
        <div className={`p-3 rounded text-sm ${
          testResult.success 
            ? "bg-green-100 text-green-700" 
            : "bg-red-100 text-red-700"
        }`}>
          {testResult.message}
        </div>
      )}

      <div className="flex gap-2 pt-4">
        <button
          onClick={handleTest}
          disabled={!dest || testing}
          className="flex-1 rounded-md border border-border bg-secondary/60 py-2 text-sm font-medium transition hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {testing ? "Testing..." : "Test Notification"}
        </button>
        <button
          onClick={() => {
            const data: any = { destination: dest };
            if (secret) data.bot_token = secret;
            onSave(data);
          }}
          className="flex-1 rounded-md bg-primary py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Save Configuration
        </button>
      </div>
    </div>
  );
}
