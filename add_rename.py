import re

with open('e:/Project/NuniMemo/web/main.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the first occurrence and add rename option
old_text = '    menu.style.top = `${e.pageY}px`;\n    \n    // Set as default option'

new_text = '''    menu.style.top = `${e.pageY}px`;
    
    // Rename option (not for root folder)
    if (folder.id !== 'root') {
        const renameOption = document.createElement('div');
        renameOption.className = 'px-4 py-2 hover:bg-slate-100 cursor-pointer text-sm flex items-center gap-2';
        renameOption.innerHTML = '<i data-lucide="edit-2" class="w-4 h-4"></i> Rename';
        renameOption.addEventListener('click', () => {
            renameFolder(folder);
            menu.remove();
        });
        menu.appendChild(renameOption);
    }
    
    // Set as default option'''

if old_text in content:
    content = content.replace(old_text, new_text, 1)
    with open('e:/Project/NuniMemo/web/main.js', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Success: Added rename option to context menu')
else:
    print('Error: Could not find the target text')
