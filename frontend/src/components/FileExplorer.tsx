import { useEffect, useRef, useState } from 'react'
import { FileText, Folder, ChevronDown, RefreshCw, Search, X, Copy, Download, Edit2 } from 'lucide-react'
import { cn } from '../utils/cn'
import { api } from '../services/api'

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  content?: string
  size?: number
  language?: string
}

const languageMap: Record<string, string> = {
  'ts': 'typescript',
  'tsx': 'typescriptreact',
  'js': 'javascript',
  'jsx': 'javascriptreact',
  'json': 'json',
  'html': 'html',
  'css': 'css',
  'scss': 'scss',
  'py': 'python',
  'rs': 'rust',
  'go': 'go',
  'java': 'java',
  'cpp': 'cpp',
  'c': 'c',
  'h': 'cpp',
  'hpp': 'cpp',
  'cs': 'csharp',
  'php': 'php',
  'rb': 'ruby',
  'swift': 'swift',
  'kt': 'kotlin',
  'dart': 'dart',
  'lua': 'lua',
  'sh': 'shell',
  'bash': 'shell',
  'zsh': 'shell',
  'fish': 'shell',
  'ps1': 'powershell',
  'sql': 'sql',
  'yaml': 'yaml',
  'yml': 'yaml',
  'toml': 'toml',
  'ini': 'ini',
  'cfg': 'ini',
  'conf': 'ini',
  'md': 'markdown',
  'txt': 'plaintext',
  'xml': 'xml',
  'svg': 'xml',
  'dockerfile': 'dockerfile',
  'gitignore': 'gitignore',
  'gitattributes': 'gitignore',
  'env': 'dotenv',
  'lock': 'json',
}

function getLanguage(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  return languageMap[ext] || 'plaintext'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface FileExplorerProps {
  projectId: string
  onFileSelect?: (file: FileNode) => void
}

export function FileExplorer({ projectId, onFileSelect }: FileExplorerProps) {
  const [fileTree, setFileTree] = useState<FileNode[]>([])
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const loadFileTree = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const data = await api.listProjectFiles(projectId)
      setFileTree(data.files || [])
      
      // Expand root folders by default
      const rootFolders = new Set<string>()
      data.files?.forEach((file: FileNode) => {
        if (file.type === 'directory') {
          rootFolders.add(file.path)
        }
      })
      setExpandedFolders(rootFolders)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFileTree()
  }, [projectId])

  const toggleFolder = (path: string) => {
    setExpandedFolders(prev => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const handleFileClick = (file: FileNode) => {
    setSelectedFile(file)
    onFileSelect?.(file)
  }

  const filteredTree = searchQuery 
    ? filterTree(fileTree, searchQuery.toLowerCase())
    : fileTree

  return (
    <div className="flex h-full bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
      {/* Sidebar - File Tree */}
      <div className="w-72 border-r border-slate-800 flex flex-col bg-slate-900">
        <div className="p-3 border-b border-slate-800 flex items-center gap-2">
          <h3 className="font-medium text-white text-sm flex-1">Files</h3>
          <button
            onClick={loadFileTree}
            disabled={loading}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors disabled:opacity-50"
            aria-label="Refresh file tree"
          >
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </button>
        </div>
        
        <div className="p-2 border-b border-slate-800">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {loading && !fileTree.length ? (
            <div className="flex items-center justify-center h-full">
              <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
            </div>
          ) : error ? (
            <div className="p-4 text-center text-red-400 text-sm">{error}</div>
          ) : filteredTree.length === 0 ? (
            <div className="p-4 text-center text-slate-500 text-sm">
              {searchQuery ? 'No files match your search' : 'No files found'}
            </div>
          ) : (
            <FileTree
              nodes={filteredTree}
              expandedFolders={expandedFolders}
              onToggleFolder={toggleFolder}
              selectedFile={selectedFile}
              onFileClick={handleFileClick}
              searchQuery={searchQuery}
            />
          )}
        </div>
      </div>

      {/* Editor Pane */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedFile && selectedFile.type === 'file' ? (
          <FileEditor
            file={selectedFile}
            onClose={() => setSelectedFile(null)}
          />
        ) : (
          <div className="flex-1 flex items-center justify-center bg-slate-950">
            <div className="text-center p-8">
              <FileText className="w-16 h-16 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-slate-400 mb-1">No file selected</h3>
              <p className="text-slate-500 text-sm">Select a file from the tree to view and edit</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface FileTreeProps {
  nodes: FileNode[]
  expandedFolders: Set<string>
  onToggleFolder: (path: string) => void
  selectedFile: FileNode | null
  onFileClick: (file: FileNode) => void
  searchQuery: string
}

function FileTree({ nodes, expandedFolders, onToggleFolder, selectedFile, onFileClick, searchQuery }: FileTreeProps) {
  return (
    <ul className="space-y-0.5" role="tree">
      {nodes.map((node) => (
        <FileTreeNode
          key={node.path}
          node={node}
          expandedFolders={expandedFolders}
          onToggleFolder={onToggleFolder}
          selectedFile={selectedFile}
          onFileClick={onFileClick}
          searchQuery={searchQuery}
          depth={0}
        />
      ))}
    </ul>
  )
}

interface FileTreeNodeProps {
  node: FileNode
  expandedFolders: Set<string>
  onToggleFolder: (path: string) => void
  selectedFile: FileNode | null
  onFileClick: (file: FileNode) => void
  searchQuery: string
  depth: number
}

function FileTreeNode({ node, expandedFolders, onToggleFolder, selectedFile, onFileClick, searchQuery, depth }: FileTreeNodeProps) {
  const isExpanded = expandedFolders.has(node.path)
  const isSelected = selectedFile?.path === node.path
  const hasChildren = node.type === 'directory' && node.children && node.children.length > 0

  if (node.type === 'directory') {
    return (
      <li role="treeitem" aria-expanded={isExpanded} aria-selected={isSelected}>
        <button
          onClick={() => onToggleFolder(node.path)}
          className={cn(
            'w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors',
            isSelected ? 'bg-blue-500/20 text-blue-400' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
          )}
          style={{ paddingLeft: `${12 + depth * 16}px` }}
        >
          <ChevronDown className={cn('w-4 h-4 flex-shrink-0 text-slate-500 transition-transform', isExpanded && 'rotate-90')} />
          <Folder className={cn('w-4 h-4 flex-shrink-0', isSelected ? 'text-blue-400' : 'text-slate-400')} />
          <span className="truncate flex-1">{node.name}</span>
          {hasChildren && (
            <span className="text-xs text-slate-500">{node.children?.length || 0}</span>
          )}
        </button>
        {isExpanded && hasChildren && (
          <ul className="space-y-0.5" role="group">
            {node.children!.map((child) => (
              <FileTreeNode
                key={child.path}
                node={child}
                expandedFolders={expandedFolders}
                onToggleFolder={onToggleFolder}
                selectedFile={selectedFile}
                onFileClick={onFileClick}
                searchQuery={searchQuery}
                depth={depth + 1}
              />
            ))}
          </ul>
        )}
      </li>
    )
  }

  return (
    <li role="treeitem" aria-selected={isSelected}>
      <button
        onClick={() => onFileClick(node)}
        className={cn(
          'w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors',
          isSelected ? 'bg-blue-500/20 text-blue-400' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
        )}
        style={{ paddingLeft: `${12 + depth * 16}px` }}
      >
        <span className="w-4 flex-shrink-0" />
        <FileText className={cn('w-4 h-4 flex-shrink-0', isSelected ? 'text-blue-400' : 'text-slate-400')} />
        <span className="truncate flex-1">{node.name}</span>
        {node.size !== undefined && (
          <span className="text-xs text-slate-500">{formatFileSize(node.size)}</span>
        )}
      </button>
    </li>
  )
}

interface FileEditorProps {
  file: FileNode
  onClose: () => void
}

function FileEditor({ file, onClose }: FileEditorProps) {
  const [content, setContent] = useState<string>(file.content || '')
  const [originalContent, setOriginalContent] = useState<string>(file.content || '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(true)
  const editorRef = useRef<HTMLDivElement>(null)
  const monacoRef = useRef<any>(null)

  useEffect(() => {
    // Load Monaco Editor dynamically
    const loadMonaco = async () => {
      if (typeof window === 'undefined') return
      
      // Check if already loaded
      if ((window as any).monaco) {
        initMonaco()
        return
      }

      // Load via CDN
      const script = document.createElement('script')
      script.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js'
      script.onload = () => {
        // Configure AMD loader
        (window as any).require.config({
          paths: {
            vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs'
          }
        })
        initMonaco()
      }
      document.head.appendChild(script)
    }

    const initMonaco = () => {
      const monaco = (window as any).monaco
      if (!monaco || !editorRef.current) return

      // Set theme
      monaco.editor.defineTheme('orion-dark', {
        base: 'vs-dark',
        inherit: true,
        rules: [],
        colors: {
          'editor.background': '#020617',
          'editor.foreground': '#f8fafc',
          'editor.lineHighlightBackground': '#0f172a',
          'editorLineNumber.foreground': '#475569',
          'editorCursor.foreground': '#0ea5e9',
          'editor.selectionBackground': '#1e293b',
          'editor.inactiveSelectionBackground': '#1e293b99',
        }
      })

      const editor = monaco.editor.create(editorRef.current, {
        value: content,
        language: file.language || getLanguage(file.name),
        theme: 'orion-dark',
        automaticLayout: true,
        minimap: { enabled: false },
        fontSize: 13,
        fontFamily: 'JetBrains Mono, monospace',
        lineNumbers: 'on',
        renderLineHighlight: 'all',
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        tabSize: 2,
        insertSpaces: true,
        bracketPairColorization: { enabled: true },
        guides: { bracketPairs: true },
      })

      monacoRef.current = editor

      editor.onDidChangeModelContent(() => {
        const newContent = editor.getValue()
        setContent(newContent)
        setSaved(newContent === originalContent)
      })

      // Handle save shortcut
      editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
        handleSave()
      })
    }

    loadMonaco()

    return () => {
      if (monacoRef.current) {
        monacoRef.current.dispose()
        monacoRef.current = null
      }
    }
  }, [file.path, content])

  const handleSave = async () => {
    if (content === originalContent) return
    
    setSaving(true)
    try {
      // Extract projectId from file path (first segment)
      const projectId = file.path.split('/')[0]
      await api.saveFileContent(projectId, file.path, content)
      
      setOriginalContent(content)
      setSaved(true)
    } catch (err) {
      console.error('Save failed:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
  }

  return (
    <div className="flex flex-col h-full bg-slate-950">
      {/* Editor Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
            aria-label="Close file"
          >
            <X className="w-4 h-4" />
          </button>
          <FileText className={cn('w-4 h-4', getLanguage(file.name) !== 'plaintext' ? 'text-blue-400' : 'text-slate-400')} />
          <span className="font-mono text-sm text-white truncate max-w-[200px]">{file.name}</span>
          {!saved && <span className="text-xs text-yellow-400">●</span>}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
            aria-label="Copy content"
            title="Copy content (Ctrl+C)"
          >
            <Copy className="w-4 h-4" />
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded transition-colors"
            aria-label="Download file"
            title="Download file"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={handleSave}
            disabled={saving || saved}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:hover:bg-slate-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            aria-label="Save file"
          >
            <Edit2 className="w-3 h-3" />
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Editor Container */}
      <div
        ref={editorRef}
        className="flex-1 overflow-hidden"
        style={{ height: '100%' }}
      />
    </div>
  )
}

function filterTree(nodes: FileNode[], query: string): FileNode[] {
  return nodes
    .map(node => {
      if (node.type === 'directory') {
        const filteredChildren = node.children ? filterTree(node.children, query) : []
        const matches = node.name.toLowerCase().includes(query) || filteredChildren.length > 0
        if (!matches) return null
        return { ...node, children: filteredChildren }
      }
      return node.name.toLowerCase().includes(query) ? node : null
    })
    .filter((node): node is FileNode => node !== null)
}

export default FileExplorer