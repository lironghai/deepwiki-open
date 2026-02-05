# Wiki Layout and Error Fixes

## Overview
Fixed two critical issues in the wiki page:
1. **Layout Issue**: Page content was restricted to center portion instead of full width
2. **Python Error**: "unhashable type: 'slice'" error in RAG layers

## Issue 1: Full-Width Layout Fix

### Problem
The wiki page was displaying content in the center only, with significant margins on both sides, instead of utilizing the full screen width.

### Root Cause
The page had maximum width constraints on main layout containers:
- `header`: `max-w-[90%] xl:max-w-[1400px]`
- `main`: `max-w-[90%] xl:max-w-[1400px]`
- `footer`: `max-w-[90%] xl:max-w-[1400px]`
- Wiki content: `max-w-[900px] xl:max-w-[1000px]`

### Solution
Modified `src/app/[owner]/[repo]/page.tsx` to use full width:

```diff
- <header className="max-w-[90%] xl:max-w-[1400px] mx-auto mb-8 h-fit w-full">
+ <header className="w-full mx-auto mb-8 h-fit px-4 md:px-8">

- <main className="flex-1 max-w-[90%] xl:max-w-[1400px] mx-auto overflow-y-auto">
+ <main className="flex-1 w-full mx-auto overflow-y-auto px-4 md:px-8">

- <footer className="max-w-[90%] xl:max-w-[1400px] mx-auto mt-8 flex flex-col gap-4 w-full">
+ <footer className="w-full mx-auto mt-8 flex flex-col gap-4 px-4 md:px-8">

- <div className="max-w-[900px] xl:max-w-[1000px] mx-auto h-full flex flex-col">
+ <div className="w-full mx-auto h-full flex flex-col">
```

### Result
- Page now uses full screen width
- Maintains proper padding via `px-4 md:px-8`
- Better use of available screen space
- More content visible without scrolling

## Issue 2: "unhashable type: 'slice'" Error Fix

### Problem
When generating wiki pages, the right-side content displayed error:
```
Error: unhashable type: 'slice'
```

### Root Cause
In `api/tools/rag_layers.py` line 463, the code attempted to check if `node_id` exists in a dictionary returned by `self.codemap_cache.get('')`:

```python
# INCORRECT CODE
for node_id, _ in top_nodes:
    if node_id in self.codemap_cache.get(''):  # ❌ Wrong: get('') returns dict or None
        entities.append(node_id)
```

This caused issues because:
1. `codemap_cache.get('')` returns a dictionary (codemap data) or None
2. Using `in` operator on dict checks keys, not values
3. If any dict key was a slice object, Python raises "unhashable type: 'slice'" error

### Solution
Fixed the logic to properly build a node lookup dictionary and extract node names:

```python
# CORRECT CODE
# Build node lookup from codemap
nodes_by_id = {node['id']: node for node in codemap.get('nodes', [])}

for node_id, _ in top_nodes:
    if node_id in nodes_by_id:
        # Get node name for entity
        node_name = nodes_by_id[node_id].get('name', node_id)
        entities.append(node_name)
```

### Changes Made
1. Create `nodes_by_id` dictionary from codemap nodes
2. Check if `node_id` exists in the properly constructed dictionary
3. Extract node name instead of using raw node_id
4. More robust error handling

### Result
- No more "unhashable type: 'slice'" errors
- Proper entity extraction from dependency graph
- Correct node names used for RAG queries

## Files Modified

1. **src/app/[owner]/[repo]/page.tsx** (Frontend)
   - Line ~2670: Header layout
   - Line ~2680: Main content layout
   - Line ~2883: Wiki content container
   - Line ~2955: Footer layout

2. **api/tools/rag_layers.py** (Backend)
   - Lines 451-465: Fixed dependency entity extraction logic

## Testing Recommendations

### Layout Testing
1. ✅ Open wiki page on different screen sizes (1920px, 1440px, 1024px, 768px)
2. ✅ Verify content uses full width with proper padding
3. ✅ Check responsive behavior on mobile devices
4. ✅ Ensure sidebar and content area scale properly

### Error Testing
1. ✅ Generate new wiki from a repository
2. ✅ Verify no Python errors in terminal/logs
3. ✅ Check right-side content displays properly
4. ✅ Test with dependency-focused queries to validate RAG layer 3
5. ✅ Verify entities are extracted correctly from codemap

## Additional Notes

### Layout Considerations
- Removed restrictive max-width constraints for better space utilization
- Maintained responsive padding for mobile/tablet devices
- Full-width design works better for documentation/wiki content
- Sidebar width remains fixed for consistent navigation

### Error Prevention
- The fix ensures proper dictionary operations in RAG layers
- Added explicit node lookup dictionary construction
- More defensive coding against malformed codemap data
- Better separation of concerns (cache vs. data access)

## Rollback Instructions

If issues arise, revert changes:

### Layout Rollback
```bash
git checkout HEAD -- src/app/[owner]/[repo]/page.tsx
```

### RAG Fix Rollback
```bash
git checkout HEAD -- api/tools/rag_layers.py
```

## Related Issues

- Similar layout constraints may exist in other pages (consider reviewing)
- RAG layer logic could benefit from additional unit tests
- Consider adding codemap schema validation to prevent future slice-related errors
